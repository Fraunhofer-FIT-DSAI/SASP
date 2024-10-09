"""
The old file referred to an apparently outdated version of the standard. This contains updates made by jan.popanda@fit.fraunhofer.de
The sappan standard has also changed and is not yet implemented here.
"""

import argparse
import json
import logging
from pymisp import ExpandedPyMISP, MISPEvent, MISPObject
from pathlib import Path
from os import makedirs, path
from sys import exit

# Event constants
event_distribution = 0
event_thr_level = 3
event_analysis_state = 2
event_info = "Security-playbook upload!"

# security-playbook - cacao playbook map
attr_map = {
    "playbook-creation-time": "created",
    "playbook-creator": "created_by",
    "description": "description",
    "playbook-id": "id",        # ZAPNUT KORELACI - spravit docker komponentu, correlate ID nic ine
    "playbook-impact": "impact",
    "playbook-modification-time": "modified",
    "playbook-abstraction": "type",  # temporary, not direct match
    "playbook-priority": "priority",
    "revoked": "revoked",
    "playbook-severity": "severity",
    "playbook-valid-from": "valid_from",
    "playbook-valid-until": "valid_until"
    # special ones :
    #"label":"labels",                  # multi-value
    #"playbook-type":"playbook-types",  # required multi-value + different value list
    #"playbook":"playbook",             # required attachment
    #"playbook-standard":"playbook-standard" # required value
    #"organization-type":"targets--name",     # deep in json
}

attr_map_sappan = {
    "playbook-creator": "HasAuthor",
    "description": "HasPlaybookPurpose",
    "playbook-id": "HasId",        # ZAPNUT KORELACI - spravit docker komponentu, correlate ID nic ine
}

# Setting up logger
LOGFORMAT = "%(asctime)-15s,%(name)s [%(levelname)s] %(message)s"
LOGDATEFORMAT = "%Y-%m-%dT%H:%M:%S"
logging.basicConfig(level=logging.INFO, format=LOGFORMAT,
                    datefmt=LOGDATEFORMAT)
logger = logging.getLogger("playbook_sharing.py")


def get_initialized_argument_parser():
    """
        Initialize ArgumentParser for command line arguments.
        :return: initialized ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description='Module loads playbook from file ')

    parser.add_argument('--playbook', '-p', action='store',
                        required=False, help='The path to the playbook file, which should be uploaded.')
    parser.add_argument('--search', '-s', action='store',
                        required=False, help='Search events with matching key words and download theirs playbooks.')
    parser.add_argument("-u", "--url", default="localhost", required=True,
                        help="URL to MISP instance")
    parser.add_argument("-k", "--key",
                        help="Automation authorization key of user", required=True)
    parser.add_argument("--cert", metavar='CA_FILE',
                        help="Use this server certificate (or CA bundle) to check the certificate of MISP instance, "
                             "useful when the server uses self-signed cert.")
    parser.add_argument("--insecure", action="store_true",
                        help="Don't check the server certificate of MISP instance.")
    parser.add_argument("-v", '--verbose', action="store_true",
                        help="Verbose mode, enables DEBUG messages of logging module")
    parser.add_argument("-q", '--quiet', action="store_true",
                        help="Disable dialog.")
    parser.add_argument('--sappan', action="store_true",
                        help="The playbook is in sappan format")

    return parser


def missing_val_handler(val, required=False):
    """
        Handle missing playbook values. Heavily depends on --quiet argument.
        :return: user input or nothing if --quiet
    """
    if args.quiet and required:
        logger.error(
            "Required attribute '%s' missing in playbook! Playbook discarded!", val)
        return None
    if args.quiet:
        return ''
    # Dialog
    if required:
        # no checks required pymisp will handle possible errors
        print("Required attribute\'", val,
              "\' missing in playbook! Please write value in console!")
    else:
        print('Attribute \'', val, '\' is missing, if you want add it manually please write value in console, otherwise just press enter to continue!')
    return input()


def send_playbook_cacao(misp_inst):
    """
        Function is used to create basic event, create security-playbook object, 
        parse misp-cacao playbook attributes, upload event with playbook to misp instance 
        :return: None
    """
    # Load playbook from file
    try:
        with open(args.playbook) as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.error("Playbook file not found!")
        exit(1)
    except json.decoder.JSONDecodeError:
        logger.error("Playbook file with invalid json format!")
        exit(1)

    # get path for attachment
    path = Path(args.playbook)  # checks performed above

    # create basic event
    ev = MISPEvent()
    ev.distribution = event_distribution
    ev.threat_level_id = event_thr_level
    ev.analysis = event_analysis_state
    ev.info = event_info

    # create object
    obj = MISPObject('security-playbook', strict=True, standalone=False)

    # assign required attributes
    obj.add_attribute('playbook-file', value=path.name, data=path, disable_correlation=True)

    if('spec_version' in data):
        obj.add_attribute('playbook-standard', value="CACAO v%s" % data['spec_version'], disable_correlation=True)
    else:
        tmp = missing_val_handler('spec_version', True)
        if (tmp == None):
            return
        obj.add_attribute('playbook-standard', value=tmp)

    if('playbook_types' in data):
        for t in data['playbook_types']:
            obj.add_attribute('playbook-type', value=t, disable_correlation=True)
    else:
        tmp = missing_val_handler('playbook_types', False)
        if (tmp == None):
            return
        elif tmp != '':
            obj.add_attribute('playbook-standard', value=tmp, disable_correlation=True)

    # assign optional attributes
    if('targets' in data):
        for x in data['targets'].values():
            if('type' in x and 'name' in x and x['type'] == 'sector'):
                obj.add_attribute('organization-type', value=x['name'], disable_correlation=True)
                break  # organization-type is not multi-value, so take first you find
    for l in data['labels']:
        obj.add_attribute('labels', value=l, disable_correlation=True)

    for attr in attr_map.items():
        if(attr[1] in data):
            obj.add_attribute(attr[0], value=data[attr[1]], disable_correlation=True)
        else:
            if(attr[1] == 'revoked'):  # dialog time saver
                continue
            tmp = missing_val_handler(attr[1], False)
            if(len(tmp) != 0):
                obj.add_attribute(attr[0], value=tmp)

    if not args.quiet:
        print('If you want add \'playbook comment\' please write comment in console, otherwise just press enter to continue!')
        tmp = input()
        if(len(tmp) != 0):
            obj.comment = tmp

    # add object to event
    ev.add_object(obj)

    # upload event to MISP instance
    event = misp_inst.add_event(ev, pythonify=True)
    logger.debug("Uploaded event id: %s", event.get('id'))

def send_playbook_sappan(misp_inst):
    """
        Function is used to create basic event, create security-playbook object, 
        parse misp-sappan playbook attributes, upload event with playbook to misp instance 
        :return: None
    """
    # Load playbook from file
    try:
        with open(args.playbook) as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.error("Playbook file not found!")
        exit(1)
    except json.decoder.JSONDecodeError:
        logger.error("Playbook file with invalid json format!")
        exit(1)

    # get path for attachment
    path = Path(args.playbook)  # checks performed above

    # create basic event
    ev = MISPEvent()
    ev.distribution = event_distribution
    ev.threat_level_id = event_thr_level
    ev.analysis = event_analysis_state
    ev.info = event_info

    # create object
    obj = MISPObject('security-playbook', strict=True, standalone=False)

    # assign required attributes
    obj.add_attribute('playbook-file', value=path.name, data=path, disable_correlation=True)

    if('HasVersion' in data['printouts']):
        obj.add_attribute('playbook-standard', value="SAPPAN v%s" % data['printouts']['HasVersion'][0], disable_correlation=True)
    else:
        tmp = missing_val_handler('HasVersion', False)
        if (tmp == None):
            return
        if(tmp != ''):
            obj.add_attribute('playbook-standard', value=tmp)

    if('HasPlaybookFocus' in data["printouts"]):
        obj.add_attribute('playbook-type', value=data['printouts']['HasPlaybookFocus'][0] + ' playbook', disable_correlation=True)
    else:
        tmp = missing_val_handler('hasPlaybookFocus', False)
        if (tmp == None):
            return
        if(tmp != ''):
            obj.add_attribute('playbook-standard', value=tmp, disable_correlation=True)


    for key,value in attr_map_sappan.items():
        if(value in data['printouts']):
            obj.add_attribute(key, value=data['printouts'][value][0], disable_correlation=True)
        else:
            if(value == 'revoked'):  # dialog time saver
                continue
            tmp = missing_val_handler(value, False)
            if(len(tmp) != 0):
                obj.add_attribute(key, value=tmp)

    if not args.quiet:
        print('If you want add \'playbook comment\' please write comment in console, otherwise just press enter to continue!')
        tmp = input()
        if(len(tmp) != 0):
            obj.comment = tmp

    # add object to event
    ev.add_object(obj)

    # upload event to MISP instance
    event = misp_inst.add_event(ev, pythonify=True)
    logger.debug("Uploaded event id: %s", event.get('id'))
    # logger.info("Uploading event to MISP instance...")


def search_events(misp_inst):
    # search events which match parameters
    complex_query = misp_inst.build_complex_query(or_parameters=str(args.search).split(','))
    events = misp_inst.search(value=complex_query, pythonify=True, with_attachments=True)
    logger.debug("Found %s matching events!" , len(events))

    # create directory for playbooks
    dir_name = './' + str(args.search).replace(" ", "_") + '/'
    if(len(events) != 0):
        makedirs(path.dirname(dir_name), exist_ok=True)
        
    # check if event contains security-playbook/s match
    for e in events:
        print(e)
        for spb in e.get_objects_by_name('security-playbook'):
            pb = spb.get_attributes_by_relation('playbook')[0] # only one playbook attribute should be present
            data = pb.get('data').getvalue().decode('utf-8')

            # Write playbook to file
            file_path = dir_name + str(pb.get('id'))+'.json'
            with open(file_path, 'w') as f:
                f.write(data)
                logger.debug("Playbook id: %s from event id: %s, saved in: %s" , pb.get('id'), e.get('id'), file_path)


def main():
    # Parse arguments
    global args
    args = get_initialized_argument_parser().parse_args()

    # set logger level
    if args.verbose:
        logger.setLevel("DEBUG")

    # MISP instance init
    cert = True  # set to check server certificate (default)
    if args.insecure:
        cert = False  # don't check certificate
    elif args.cert:
        cert = args.cert  # read the certificate (CA bundle) to check the cert
    url = args.url if args.url.startswith("http") else "https://" + args.url

    misp_inst = ExpandedPyMISP(url, args.key, cert)

    # Search and download playbooks
    if(args.search is not None):
        search_events(misp_inst)
        
    # Upload playbook
    if(args.playbook is not None):
        if args.sappan:
            send_playbook_sappan(misp_inst)
        else:
            send_playbook_cacao(misp_inst)
        
    # No parameters warning
    if(args.playbook is None and args.search is None):
        logger.error("Nothing to do here! No upload or download parameters provided!")
        exit(1)


if __name__ == "__main__":
    main()
