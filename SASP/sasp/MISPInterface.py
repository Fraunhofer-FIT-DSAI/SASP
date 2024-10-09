from pymisp import ExpandedPyMISP, MISPEvent, MISPObject
from pymisp.exceptions import PyMISPError
import logging
import json
import tempfile
from base64 import b64decode
from pathlib import Path
from django.contrib.auth.models import User

class MISPInterface:
    logger = logging.getLogger(__name__)
    quiet = False

    # Event constants
    event_distribution = 0
    event_thr_level = 3
    event_analysis_state = 2
    event_info = "Security-playbook upload!"

    # Attribute mapping
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

    def __init__(self, user=""):
        if user == "":
            user = "default"
        
        user = User.objects.get(username=user).profile
        login = user.logins.get(name='misp')
        self.user_id = user.get_unique_id()
        try:
            if login.cert:
                self.misp_inst = ExpandedPyMISP(login.url, login.token, login.cert)
            else:
                self.misp_inst = ExpandedPyMISP(login.url, login.token, False)
        except PyMISPError as e:
            self.logger.error("MISP connection error: %s", e)
            raise e



    def _search(self,search_string):
        """
        Search for events containing the given search string and a playbook object.
        Internal function, use search() instead.
        Args:
            search_string (str): search string to search for in MISP events
        Returns:
            list: list of matching events
        """
        complex_query = self.misp_inst.build_complex_query(or_parameters=[x.strip() for x in str(search_string).split(',')])
        events = self.misp_inst.search(value=complex_query,pythonify=True)
        self.logger.info("Found %s matching events!" , len(events))

        matches = []
            
        # check if event contains security-playbook/s match
        for e in events:
            # for _ in e.get_objects_by_name('security-playbook'):
            matches.append(e)
        return matches

    def search(self,search_string):
        """
        Search for events containing the given search string and a playbook object.
        Args:
            search_string (str): search string to search for in MISP events
        Returns:
            dict: Keys are headers, values are lists of matching events
        """
        matches = self._search(search_string)

        # playbook-id (optional) 	text 	A value that (uniquely) identifies the playbook. If the playbook itself embeds an identifier then the playbook-id SHOULD use the same identifier (value) for correlation purposes.
        # description (optional) 	text 	An explanation, details, and more context about what this playbook does and tries to accomplish.
        # revoked (optional) 	boolean 	A boolean that identifies if the playbook is no longer valid (revoked).
        # playbook-creation-time (optional) 	datetime 	The date and time at which the playbook was originally created.
        # playbook-modification-time (optional) 	datetime 	The date and time at which the playbook was last modified.
        # playbook-valid-from (optional) 	datetime 	The date and time from which the playbook is considered valid and the steps that it contains can be executed.
        # playbook-valid-until (optional) 	datetime 	The date and time from which the playbook should no longer be considered a valid playbook to be executed.
        # playbook-creator (optional) 	text 	The entity that created the playbook. It can be a natural person or an organization. It may be represented using a unique identifier that identifies the creator.
        # labels (optional) 	text 	Labels for this playbook (e.g., adversary persona names, associated groups, malware family/variant/name that this playbook is related to). Another option is to use MISP tags, taxonomies, and galaxies.
        # organization-type (optional) 	text 	The type of organization that the playbook is intended for. This can be an industry sector. Another option is to use MISP tags, taxonomies, and galaxies.
        # playbook-standard (optional) 	text 	The standard/format/notation the playbook conforms to (e.g., CACAO, BPMN).
        # playbook-abstraction (optional) 	text 	The playbook’s level of abstraction (with regards to consumption). Listed options: [template, executable]
        # playbook-type (optional) 	text 	The security-related functions the playbook supports. A playbook may account for multiple types (e.g., detection and investigation). The listed options are based on the CACAO standard and NIST SP 800-61 rev2. Another option is to use MISP tags, taxonomies, and galaxies. Listed options: [notification, detection, investigation, prevention, mitigation, remediation, analysis, containment, eradication, recovery, attack]
        # playbook-impact (optional) 	text 	From 0 to 100, a value representing the impact the playbook has on the organization. A value of 0 means specifically undefined. Impact values range from 1, the lowest impact, to a value of 100, the highest. For example, a purely investigative playbook that is non-invasive could have a low impact value of 1. In contrast, a playbook that performs changes such as adding rules into a firewall should have a higher impact value.
        # playbook-severity (optional) 	text 	From 0 to 100, a value representing the seriousness of the conditions that this playbook addresses. A value of 0 means specifically undefined. Severity values range from 1, the lowest severity, to a value of 100, the highest.
        # playbook-priority (optional) 	text 	From 0 to 100, a value representing the priority of this playbook relative to other defined playbooks. A value of 0 means specifically undefined. Priority values range from 1, the highest priority, to a value of 100, the lowest.
        # playbook-file (requiredOneOf) 	attachment 	The entire playbook file/document in its native format (e.g., CACAO JSON or BPMN).
        # playbook-base64 (requiredOneOf) 	text 	The entire playbook encoded in base64.

        # create dict with headers as keys and list of matching events as values
        headers = ['Event-ID', 'ID', 'Revoked', 'Modified', 'Valid from', 'Valid until', 'Creator', 'Labels', 'Standard']
        attributes = ['playbook-id', 'revoked', 'playbook-modification-time', 'playbook-valid-from', 'playbook-valid-until', 'playbook-creator', 'labels', 'playbook-standard']
        data = {h: [] for h in headers}
        for event in matches:
            pb = event.get_objects_by_name('security-playbook')[0]

            data['Event-ID'].append(event.get('id'))
            
            for i, attr in enumerate(attributes):
                value = pb.get_attributes_by_relation(attr)
                if len(value) == 0:
                    value = 'N/A'
                elif len(value)==1:
                    value = value[0].get('value')
                else:
                    value = ", ".join(a.get('value') for a in value)
                data[headers[i+1]].append(value)

        return data

    def get_event(self,event_id):
        """
        Get event from MISP instance
        Args:
            event_id (int): event id to get from MISP
        Returns:
            MISPEvent: event object
        """
        return self.misp_inst.get_event(event_id, pythonify=True)

    def get_playbook(self,event_id):
        """
        Gets a formatted dictionary of the playbook object from the event
        Args:
            event_id (int): event id to get from MISP
        Returns:
            dict: playbook object
        """
        event = self.get_event(event_id)
        try:
            pb_obj = event.get_objects_by_name('security-playbook')[0]
        except IndexError:
            raise Exception("No playbook object found in event!")
        
        # playbook-id (optional)
        # description (optional)
        # revoked (optional)
        # playbook-creation-time (optional)
        # playbook-modification-time (optional)
        # playbook-valid-from (optional)
        # playbook-valid-until (optional)
        # playbook-creator (optional)
        # labels (optional)
        # organization-type (optional)
        # playbook-standard (optional)
        # playbook-abstraction (optional)
        # playbook-type (optional)
        # playbook-impact (optional)
        # playbook-severity (optional)
        # playbook-priority (optional)
        # playbook-file (requiredOneOf)
        # playbook-base64 (requiredOneOf)

        optional_attrs = [
            'playbook-id',
            'description',
            'revoked',
            'playbook-creation-time',
            'playbook-modification-time',
            'playbook-valid-from',
            'playbook-valid-until',
            'playbook-creator',
            'labels',
            'organization-type',
            'playbook-standard',
            'playbook-abstraction',
            'playbook-type',
            'playbook-impact',
            'playbook-severity',
            'playbook-priority',
        ]

        return_dict = {}
        for attr in optional_attrs:
            value = pb_obj.get_attributes_by_relation(attr)
            if len(value) == 0:
                continue
            else:
                return_dict[attr] = [str(a.get('value')) for a in value]
        
        # If playbook-file is present, return it as a string
        value = pb_obj.get_attributes_by_relation('playbook-file')
        if len(value) != 0:
            return_dict['playbook-file'] = value[0].get('data').getvalue().decode('utf-8')
        # If playbook-base64 is present, decode it and save it as playbook-file
        # and keep the base64 string in the dictionary because it looks impressive
        value = pb_obj.get_attributes_by_relation('playbook-base64')
        if len(value) != 0:
            return_dict['playbook-base64'] = [str(a.get('value')) for a in value]
            return_dict['playbook-file'] = b64decode(value[0].get('value')).decode('utf-8')

        return return_dict
        



    def retrieve_playbook(self,event_id,playbook):
        """
        Re-retrieve the event from MISP with attachments and return the playbook object as a string
        """
        # TODO: Run with print output to see what each object looks like
        event = self.misp_inst.get_event(event_id, pythonify=True)
        for spb in event.get_objects_by_name('security-playbook'):
            pb = spb.get_attributes_by_relation('playbook-file')
            if len(pb) == 0:
                pb = spb.get_attributes_by_relation('playbook-base64')
                if len(pb) == 0:
                    raise Exception("No playbook file found in event!")
                pb = pb[0]
                data = b64decode(pb.get('value')).decode('utf-8')
            else:
                pb = pb[0]
                data = pb.get('data').getvalue().decode('utf-8')
            return data

    def send_sapppan_playbook(playbook, name):
        """
        Send a sappan playbook to MISP
        Args:
            playbook (str): playbook to send to MISP (json)
        """
        return False, ["SAPPAN playbooks are not supported yet!"]

    def send_playbook_cacao(self,playbook, name):
        """
            Function is used to create basic event, create security-playbook object, 
            parse misp-cacao playbook attributes, upload event with playbook to misp instance 
            Args:
                playbook (str): playbook to send to MISP (json)

        """
        # Load playbook from string
        try:
            data = json.loads(playbook)
        except json.decoder.JSONDecodeError:
            self.logger.error("Playbook file with invalid json format!")
            return False, ["Playbook file with invalid json format!"]

        with tempfile.TemporaryDirectory() as tmpdirname:
            path = Path(tmpdirname) / f"{name}.json"
            with open(path, 'w') as f:
                f.write(playbook)
            

            # create basic event
            ev = MISPEvent()
            ev.distribution = self.event_distribution
            ev.threat_level_id = self.event_thr_level
            ev.analysis = self.event_analysis_state
            ev.info = self.event_info

            # create object
            obj = MISPObject('security-playbook', strict=True, standalone=False)

            # assign required attributes
            obj.add_attribute('playbook-file', value=path.name, data=path, disable_correlation=True)

            if('spec_version' in data):
                obj.add_attribute('playbook-standard', value="CACAO v%s" % data['spec_version'], disable_correlation=True)

            if('playbook_types' in data):
                for t in data['playbook_types']:
                    obj.add_attribute('playbook-type', value=t + ' playbook', disable_correlation=True)

            # assign optional attributes
            if('targets' in data):
                for x in data['targets'].values():
                    if('type' in x and 'name' in x and x['type'] == 'sector'):
                        obj.add_attribute('organization-type', value=x['name'], disable_correlation=True)
                        break  # organization-type is not multi-value, so take first you find
            if('labels' in data):
                for l in data['labels']:
                    obj.add_attribute('labels', value=l, disable_correlation=True)

            for attr in self.attr_map.items():
                if(attr[0] == 'playbook-creator'):
                    obj.add_attribute('playbook-creator', value=self.user_id, disable_correlation=True)
                    continue
                if(attr[1] in data):
                    obj.add_attribute(attr[0], value=data[attr[1]], disable_correlation=True)

            # add object to event
            ev.add_object(obj)

            # upload event to MISP instance
            event = self.misp_inst.add_event(ev, pythonify=True)
            self.logger.debug("Uploaded event id: %s", event.get('id'))
            return True, []
        
    def missing_val_handler(self,val, required=False):
        """
            Handle missing playbook values. Heavily depends on --quiet argument.

            Modified from playbook_sharing.py. Doesn't allow for user input and auto fails if required value is missing.
            Also returns errors as a list in addition to printing them.
            :return: user input or nothing if --quiet
        """
        if required:
            error = "Required attribute '%s' missing in playbook! Playbook discarded!" % val
            self.logger.error(error)
            return {
                "value": None,
                'errors': [error]
            }
        return {
            "value": '',
            'errors': []
        }

    def test_send_cacao(self):
        with open('DGA.json') as f:
            data_str = json.dumps(json.load(f))

        self.send_playbook_cacao(data_str, 'DGA')

    def test_search(self):
        for event in self._search('DGA'):
            pb = event.get_objects_by_name('security-playbook')[0]
            event_id = event.get('id')

            pb_filename = pb.get_attributes_by_relation('playbook-file')[0].get('value')
            pb_types = ", ".join(a.get('value') for a in pb.get_attributes_by_relation('playbook-type'))
            pb_labels = ", ".join(a.get('value') for a in pb.get_attributes_by_relation('labels'))
            pb_created = pb.get_attributes_by_relation('playbook-creation-time')[0].get('value')

            print(f"Event ID: {event_id}")
            print(f"Playbook filename: {pb_filename}")
            print(f"Playbook types: {pb_types}")
            print(f"Playbook labels: {pb_labels}")
            print(f"Playbook created: {pb_created}")

    def test_retrieve(self):
        from pprint import pprint
        pprint(self.retrieve_playbook(2, 'DGA'))