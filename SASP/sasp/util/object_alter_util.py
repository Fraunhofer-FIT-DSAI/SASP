from collections import Counter

from pm4py.algo.discovery.alpha.variants.classic import apply_dfg_sa_ea
from util.bpmn_util import convert_petri_to_bpmn
import util.vocabulary_translator as vt
import sasp.knowledge as knowledge
import logging

logger = logging.getLogger(__name__)

def get_instance_info(site, name):
    """Retrieves all the instance (eg. playbook) information from the wiki in
    a psuedo RDF triple format List[(name, instance_info[0], instance_info[1])]

    Args:
        site (Site): Wiki instance
        name (str): Name of the instance to get the information from

    Returns:
        List[Tuple[str, str]]: Predicates and Objects of the triples.
    """
    logger.debug(f'Getting instance info for {name}')
    page = site.pages[name]

    # isolate the instance info
    t = page.text().split('{{',1)[1]
    t = t.split('}}',1)[0]

    # split the instance info into predicates and objects
    entries = {prop.strip():values.strip() for prop,values in [x.split('=',1) for x in t.split('|')[1:]]}
    instance_info = []
    for prop,values in entries.items():
        instance_info.append((prop, values))
    return instance_info


def get_instance_info_wide(site, name):
    """Retrieves all the instance (eg. playbook) information from the wiki in
    a psuedo RDF triple format. The wide format splits any multiple token line
    into each its own predicate and object tuple.

    Args:
        site (Site): Wiki instance
        name (str): Name of the instance to get the information from

    Returns:
        List[Tuple[str, str]]: Predicates and Objects of the triples.
    """
    page_info = get_instance_info(site, name)
    page_prop_tuples = []

    try:
        for prop, value in page_info:
            if ',' in value and prop not in knowledge.FREE_TEXT_FIELDS:
                page_prop_tuples.extend([(prop, value_.strip()) for value_ in value.split(',')])
            else:
                page_prop_tuples.append((prop, value))
    except Exception as e:
        logger.error(f'Error getting instance info for {name}')
        logger.error(e)
        raise e

    return page_prop_tuples


def create_instance_query(instance, form):
    """Creates an instance query required to submit the new instance
    information to the wiki via an api call.

    Args:
        instance (List[Tuple[str, str]]): Wide tuple list of the instance
        form (str): Name of the form used to create the instance

    Returns:
        str: Valid query that can be used with the wiki api
    """
    if isinstance(instance, list):
        instance = wide_tup_list_to_dict(instance)

    query_list = []
    for k, v in instance.items():
        if k in vt.default_values and v == '':
            query_list.append(f'{form}[{k}]={vt.default_values[k]}')
        else:
            v = v.replace('/', '-')
            variations = {k}
            # form fields are case sensitive, so I can either guess which entry I have to change in over 40 files
            # or I can just add duplicates for the case of the key
            variations.add(k.replace('_', ' ').title())
            variations.add(k.title().replace('_', ' '))
            variations.add(k.title())
            for variation in variations:
                query_list.append(f'{form}[{variation}]={v}')
    
    logger.debug(f'Query: {"&".join(query_list)}')

    return '&'.join(query_list)


def wide_tup_list_to_dict(instance_tups):
    """Converts a wide tuple list into a dictionary. This essentially makes
    it narrow and then converts it into a dictionary. This is mainly required
    for the use in creating an instance query.

    Args:
        instance_tups (List[Tuple[str, str]]): Wide tuple list of the instance

    Returns:
        Dict: Narrow tuple list as a dictionary
    """
    new_dict = {}
    for attr, value in instance_tups:
        if attr in new_dict:
            new_dict[attr] = f'{new_dict[attr]},{value}'
        else:
            new_dict[attr] = value

    return new_dict


def generate_bpmn(site, playbook,playbook_type="Playbook"):
    """Generate a bpmn from step links attached to the target playbook.
    The function retrieves the playbook and steps information from the wiki,
    converts it into a DFG, applies the basic alpha miner of the DFG and
    finally converts the resulting accepting petri net into a bpmn graph.

    Args:
        site (Site): Wiki instance.
        playbook (List[Tuple[str, str]]): Tool internal wide playbook instance
        playbook_type (str): Type of the playbook.

    Returns:
        BPMN: bpmn graph object
    """
    dfg = Counter()
    # related to start steps
    sa = {}
    # related to end steps
    ea = {}
    # contains all the steps
    steps_dict = {}

    logger.debug("Playbook type: %s\nPlaybook: %s",playbook_type,playbook)
    if playbook_type == "Playbook":
        # get all step names
        for t in playbook:
            if t[0] in {'hasInitialStep', 'hasFinalStep',
                        'hasIntermediateStep', 'hasExclusiveChoiceStep'} and t[1]:
                if t[0] == 'hasInitialStep':
                    sa[t[1]] = 1
                elif t[0] == 'hasFinalStep':
                    ea[t[1]] = 1
                instance = get_instance_info_wide(site, t[1])
                steps_dict[t[1]] = [ns[1] for ns in instance
                                    if ns[0] == 'hasNextStep']
    elif playbook_type == "CACAO Playbook":
        # get all step names
        for prop,value in playbook:
            logger.debug("Prop: %s, Value: %s",prop,value)
            if prop == 'workflow_start':
                logger.debug("Start step: %s",value)
                sa[value] = 1
            elif prop == 'workflow' and value:
                if not site.pages[value].exists:
                    continue
                instance = get_instance_info_wide(site, value)
                for p,v in instance:
                    if p in {   'on_completion',
                                'on_success',
                                'on_failure',
                                'on_true',
                                'on_false',
                                'next_steps',
                                'cases'
                            }:
                        
                        if site.pages[v].exists:
                            steps_dict[value] = steps_dict.get(value, []) + [v]
                    elif p=='Type' and v=='end':
                        ea[value] = 1
    # prepare loop
    seen_steps = {s for s in sa}
    check_steps = {s for s in sa}

    while check_steps:
        new_steps = check_steps
        check_steps = []
        for step in new_steps:
            src = step
            for tar in steps_dict.get(src, []):
                dfg[(src, tar)] = 1

                if tar not in seen_steps:
                    check_steps.append(tar)
                    seen_steps.add(tar)

    logger.debug("Counter: %s, Start: %s, End: %s",dfg, sa, ea)
    petri, im, fm = apply_dfg_sa_ea(dfg, sa, ea)
    bpmn_graph = convert_petri_to_bpmn(petri, im, fm)

    return bpmn_graph
