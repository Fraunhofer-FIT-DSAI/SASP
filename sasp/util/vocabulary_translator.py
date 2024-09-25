import uuid,json
from collections import defaultdict
# sapppan:cacao
playbook_equivalents = {
    'hasPlaybookPurpose': 'description',
    'hasPreCondition': None,
    'hasPostCondition': None,
    'hasConfidentiality': None,
    'isLicencedUnder': None,
    'hasAuthor': 'created_by',
    # 'hasPlaybookFocus': 'playbook_types',
    'hasPlaybookCategory': None,
    'hasPlaybookState': None,
    'hasRelationshipToGovernance': None,
    'hasPrecondition': None,
    'hasPostcondition': None,
    'isLicensedUnder': None,
    'hasVersion': 'spec_version',
    'hasId': 'id',
    'hasDisplayName': 'name',
    'hasComment': 'description'
}

# cacao:sappan
step_types_equivalents = {
    'start': 'InitialStep',
    'single': 'IntermediateStep',
    'end': 'FinalStep',
    # 'optionalStep': '',
    # 'indicatorStep': '',
    'if-condition': 'ExclusiveChoiceStep'
}

# cacao:sappan
step_prop_equivalents = {
    'name': 'name',
    'description': 'description',
    'on_completion': 'hasNextStep',
    'on_true': 'hasNextStep',
    'on_false': 'hasNextStep'
    # 'prevstep': None
}

type_to_form_sappan = {
    'InitialStep': 'Initial Step',
    'FinalStep': 'Final Step',
    'IntermediateStep': 'Intermediate Step',
    'ExclusiveChoiceStep': 'Exclusive Choice Step',
    'OptionalStep': 'Optional Step',
    'Playbook': 'Playbook',
}

type_to_form_cacao_steps = {
    'start': 'Start Step',
    'end': 'End Step',
    'single': 'Single Action Step',
    'if-condition': 'If Condition Step',
    'parallel': 'Parallel Step',
    'playbook': 'Playbook Step',
    'switch-condition': 'Switch Condition Step',
    'while-condition': 'While Condition Step'    
}

type_to_form_cacao_targets = {
    'individual': 'Individual Target',
    'group': 'Group Target',
    'organization': 'Organization Target',
    'location': 'Location Target',
    'sector': 'Sector Target',
    'http-api': 'HTTP API Target',
    'ssh' : 'SSH CLI Target',
    'security-infrastructure-category': 'Security Infrastructure Category Target',
    'net-address': 'General Network Address Target',
    'kali' : 'Kali Linux Target',
    'attacker': 'Attacker Target',
    'attack-agent': 'Attack Agent Target',
    'attack-group': 'Attack Group Target'
}

type_to_form_cacao_data_marking = {
    'marking-statement': 'Statement Marking',
    'marking-tlp': 'TLP Marking',
    'marking-iep': 'IEP Marking'
}

form_to_type_cacao = dict()
for key,value in (type_to_form_cacao_steps | type_to_form_cacao_targets | type_to_form_cacao_data_marking).items():
    form_to_type_cacao[value] = key


prop_to_form_sappan = {
    'hasInitialStep': 'Initial Step',
    'hasFinalStep': 'Final Step',
    'hasIntermediateStep': 'Intermediate Step',
    'hasExclusiveChoiceStep': 'Exclusive Choice Step',
    'hasOptionalStep': 'Optional Step',
    'performAction': 'Action',
    'useTool': 'Tool'
}

prop_to_form_cacao = {    
    'external_references': lambda _: 'External Reference',
    'playbook_variables': lambda _: 'Variable',
    'step_variables': lambda _: 'Variable',
    'workflow': lambda x: type_to_form_cacao_steps[x['type']],
    'targets': lambda x: type_to_form_cacao_targets[x['type']],
    'extension_definitions': lambda _: 'Extension',
    'data_marking_definitions' : lambda x: type_to_form_cacao_data_marking[x['type']],
    'signatures': lambda _: 'Signature',
    'step_extensions': lambda _: 'Extension',
    'commands': lambda _: 'Command',
    'target_extensions': lambda _: 'Extension',
    'contact': lambda _: 'Contact Information',
    'location': lambda _: 'Civic Location',
    'gps': lambda _: 'GPS Location',
    'marking_extensions': lambda _: 'Extension',
    
}

type_to_prop = {
    'InitialStep': 'hasInitialStep',
    'FinalStep': 'hasFinalStep',
    'IntermediateStep': 'hasIntermediateStep',
    'ExclusiveChoiceStep': 'hasExclusiveChoiceStep',
    'OptionalStep': 'hasOptionalStep',
    'Playbook': 'isStepOf',
}

default_values = {
    'hasConfidentiality': 'd - TLP:RED',
    'hasPlaybookState': 'Work-in-progress',
    'hasPlaybookFocus': 'Preparation',
    'hasPlaybookCategory': 'Playbook',
    'mean': 'Detection'
}

add_to_playbook = {
    'Final Step': ['hasFinalStep'],
    'Initial Step': ['hasInitialStep'],
    'Intermediate Step': ['hasIntermediateStep'],
    'Exclusive Choice Step': ['hasExclusiveChoiceStep'],
    'Attack Agent Target': ['targets'],
    'Attack Group Target': ['targets'],
    'Attacker Target': ['targets'],
    'General Network Address Target': ['targets'],
    'Group Target': ['targets'],
    'HTTP API Target': ['targets'],
    'Individual Target': ['targets'],
    'Kali Linux Target': ['targets'],
    'Location Target': ['targets'],
    'Organization Target': ['targets'],
    'SSH CLI Target': ['targets'],
    'Sector Target': ['targets'],
    'Security Infrastructure Category Target': ['targets'],
    'IEP Marking': ['markings','data_marking_definitions'],
    'Statement Marking': ['markings','data_marking_definitions'],
    'TLP Marking': ['markings','data_marking_definitions'],
    'End Step': ['workflow'],
    'If Condition Step': ['workflow'],
    'Parallel Step': ['workflow'],
    'Playbook Step': ['workflow'],
    'Single Action Step': ['workflow'],
    'Start Step': ['workflow','workflow_start'],
    'Switch Condition Step': ['workflow'],
    'While Condition Step': ['workflow'],
    'Extension': ['extension_definitions'],
    'External Reference': ['external_references'],
    'Signature': ['Signatures'],
    'Variable': ['playbook_variables'],
}

def _match_step_to_next_field(prev_step_form):
    """Helper function to match a step to the next field

    Args:
        prev_step_form (str): The previous step form

    Returns:
        list: A list of tuples of the form ("one" | "all", ["field_name_1", "field_name_2", ...])
    """
    if prev_step_form == 'Start Step':
        return [("one",['on_completion', 'on_success', 'on_failure'])]
    elif prev_step_form == 'Single Action Step':
        return [("one",['on_completion', 'on_success', 'on_failure'])]
    elif prev_step_form == 'Playbook Step':
        return [("one",['on_completion', 'on_success', 'on_failure'])]
    elif prev_step_form == 'Parallel Step':
        return [("all",["next_steps"])]
    elif prev_step_form == 'If Condition Step':
        return [("one",['on_true', 'on_false'])]
    elif prev_step_form == 'Switch Condition Step':
        return [("all",["cases"])]
    # SAPPAN steps
    elif prev_step_form in {'Initial Step', 'Intermediate Step', 'Exclusive Choice Step', 'Optional Step'}:
        return [("all",['hasNextStep'])]

# TODO: Targets need to exclusively choose betweem target or target_ids
add_to_child = {
    'Action': ['performAction'],
    'Tool': ['useTool'],
    'GPS Location': ['gps'],
    'Variable': ['step_variables'],
    'External Reference': ['External References'],
    'Extension': ['Step extensions'],
    'Command': ['commands'],
    'Contact Information': ['contact'],
    'Attack Agent Target': ['target','target_ids'],
    'Attack Group Target': ['target','target_ids'],
    'Attacker Target': ['target','target_ids'],
    'General Network Address Target': ['target','target_ids'],
    'Group Target': ['target','target_ids'],
    'HTTP API Target': ['target','target_ids'],
    'Individual Target': ['target','target_ids'],
    'Kali Linux Target': ['target','target_ids'],
    'Location Target': ['target','target_ids'],
    'Organization Target': ['target','target_ids'],
    'SSH CLI Target': ['target','target_ids'],
    'Sector Target': ['target','target_ids'],
    'Security Infrastructure Category Target': ['target','target_ids'],
    "End Step": _match_step_to_next_field,
    "Single Action Step": _match_step_to_next_field,
    "Playbook Step": _match_step_to_next_field,
    "Parallel Step": _match_step_to_next_field,
    "If Condition Step": _match_step_to_next_field,
    "Switch Condition Step": _match_step_to_next_field,
    "While Condition Step": _match_step_to_next_field,
    "Exclusive Choice Step": _match_step_to_next_field,
    "Final Step": _match_step_to_next_field,
    "Intermediate Step": _match_step_to_next_field,
    "Optional Step": _match_step_to_next_field,
}

add_parent_info = {
    'Exclusive Choice Step': ['hasPreviousStep'],
    'Final Step': ['hasPreviousStep'],
    'Intermediate Step': ['hasPreviousStep'],
    'Optional Step': ['hasPreviousStep'],
}

cacao_property_aliases = {
    'email': 'email-address'
}
def cacao_property_aliases_func(prop):
    """Helper function if the property has an alias on the smw side
    e.g. email -> email-address
    Args:
        prop (str): The property name
    Returns:
        str: The property name or if it exists, the alias.
    """
    if prop in cacao_property_aliases:
        return cacao_property_aliases[prop]
    return prop

def convert_cacao_prop_to_form(prop,value=None):
    """Helper function to connect a CACAO property to it's form
    Args:
        prop (str): CACAO property
        value (str): CACAO object
    Returns:
        str: form property
    """
    if prop in prop_to_form_cacao:
        return prop_to_form_cacao[prop](value)
    return prop

# Special cases where the cacao and smw format clash
cacao_special_cases = {
    ("playbook","features"): lambda d: [key for key in d if d[key]], # Is a dictionary with the key being the name of the feature and the value being a boolean. Easy to convert to a list.
    ('switch-condition', 'cases'): lambda d: [item for sublist in d.values() for item in sublist], # Converts cases into a list. Correspondence between case name and step is preserved elsewhere
    ('net-address','address'): lambda d: [f'{key}: {value}' for key,value in d], # Join key and value into a single string
    'email': lambda d: [f'{key}: {value}' for key,value in d], # Join key and value into a single string
    'phone': lambda d: [f'{key}: {value}' for key,value in d], # Join key and value into a single string
}

def is_command(obj):
    """Helper function to identify commands because they need to be special little things that don't fit the normal pattern

    Args:
        obj (dict): The object in question

    Returns:
        bool: True if a command. Otherwise False.
    """
    command_types = {
        'manual',
        'http-api',
        'ssh',
        'bash',
        'openc2-json',
        'attack-cmd',
        'sigma',
        'jupyter',
        'kestrel'
    }
    return obj.get('type') in command_types

def is_variable(obj):
    """Helper function to identify variables because they need to be special little things that don't fit the normal pattern

    Args:
        obj (dict): The object in question

    Returns:
        bool: True if a variable. Otherwise False.
    """
    return obj.get('type') in {"string","uuid","integer","long","mac-addr","ipv4-addr","ipv6-addr","uri","sha256-hash","hexstring","dictionary"}

def generate_page_title_cacao(object:dict,parent_title:str,index:int=None) -> str:
    """Generates a page title for the given object. Only use if the object has no identifier.
    Args:
        object (dict): The object in question
        parent_title (str): The title of the parent object
        index (int): The index of the object in the parent object, defaults to None
    Returns:
        str: The page title
    """
    obj_title = ''
    if 'id' in object:
        obj_title = parent_title + ': ' + object['id']
    elif 'name' in object:
        obj_title = parent_title + ': ' + object['name']
    elif is_command(object):
        obj_title = parent_title + ': ' + object['type'] + ' command'
    if index is not None:
        obj_title = obj_title + ' ' + str(index)
    assert obj_title != '', "No title for object: " + str(object)
    return obj_title
    
def sanitize_mediawiki_value(value):
    """Helper function to sanitize values for MediaWiki, replacing problematic characters with their MediaWiki equivalents.
    Args:
        value (str): The value to sanitize
    Returns:
        str: The sanitized value
    """
    char_map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '\n': '<br>',
        '\r': '',
        ',' : '',
        ';' : '',
        '|' : '',
    }

    if value is None:
        return ''

    value = str(value)
    for char, replacement in char_map.items():
        value = value.replace(char, replacement)
    return value

# NOTE below
"""
Write recursive function which receives a dictionary, a page title and a form name.
Output is saved in shared dictionary (defaultdict) where key is tuple (page title,form name), which apparently you can do,
and value is list of property tuples in the form [(property_name, property_value)].
For multiple entries in the same property add multiple tuples. [(prop_1,value_1),(prop_2,value_2),(prop_1,value_3)]
Function goes through each key like this:
    if key is in cacao_prop_to_form:
        Call self with value, new page title and form name
        Make sure to distinguish between dictionaries and lists
        Remember to add property to own dictionary
    elif key is in cacao_special_cases:
        Call function defined for special case.
    finally:
        Use keys as properties, check for aliases in cacao_property_aliases, 
        and value(s) as values. Add to shared dictionary under (page title,form_name).
    Merge shared dictionary and return.
"""

def parse_cacao_object(obj:dict,page_title:str,form_name:str) -> dict:
    """Converts a cacao_object to a dictionary where the key is a tuple of (page_title,form_name) 
    ant the value is a list of pseudo rdf tuples in the form [(property_name, property_value)].
    Recursive parses the object and its children.

    Args:
        obj (dict): The cacao object to parse
        page_title (str): The page title of the object
        form_name (str): The form name of the object

    Returns:
        dict: A dictionary where the key is a tuple of (page_title,form_name)
        and the value is a list of pseudo rdf tuples in the form [(property_name, property_value)].
    """
    shared_dict = defaultdict(list)
    for key,value in obj.items():
        if key in prop_to_form_cacao: # If key is in cacao_prop_to_form, call self with value, new page title and form name
            if isinstance(value,dict) and 'type' in value: # If value is a dictionary and has a type key, it is a CACAO object
                new_page_title = generate_page_title_cacao(value,page_title)
                shared_dict.update(
                    parse_cacao_object(
                        value,
                        new_page_title,
                        prop_to_form_cacao[key](value)
                    )
                )
                shared_dict[(page_title,form_name)].append(
                    (
                        cacao_property_aliases_func(key),
                        new_page_title
                    )
                )
            elif isinstance(value,list): # If value is a list, it is a list of CACAO objects
                for i,object in enumerate(value):
                    new_page_title = generate_page_title_cacao(object,page_title,None if i == 0 or not is_command(object) else i)
                    shared_dict.update(
                        parse_cacao_object(
                            object,
                            new_page_title,
                            prop_to_form_cacao[key](object)
                        )
                    )
                    shared_dict[(page_title,form_name)].append(
                        (
                            cacao_property_aliases_func(key),
                            new_page_title
                        )
                    )
            # If value is a dictionary and has any variables, it is a dictionary of variables
            # This is a special case because variables are likely to reuse the same name, so we need to assign them to our page title
            elif isinstance(value,dict) and any(is_variable(v) for v in value.values()): 
                for identifier,object in value.items():
                    new_page_title = page_title + ": " + identifier
                    shared_dict.update(
                        parse_cacao_object(
                            object,
                            new_page_title,
                            prop_to_form_cacao[key](object)
                        )
                    )
                    shared_dict[(page_title,form_name)].append((cacao_property_aliases_func(key),new_page_title))
            elif isinstance(value,dict): # If value is a dictionary, but does not contain type it is assumed to be of the form {'identifier':'cacao object'}
                for identifier,object in value.items():
                    shared_dict.update(
                        parse_cacao_object(
                            object,
                            identifier,
                            prop_to_form_cacao[key](object)
                        )
                    )
                    shared_dict[(page_title,form_name)].append((cacao_property_aliases_func(key),identifier))
        # If key is in cacao_special_cases, call associated function
        elif (obj.get('type'),key) in cacao_special_cases: # Tuple necessary to distinguish between different uses of same property name
            for value_ in cacao_special_cases[(obj.get('type'),key)](value):
                shared_dict[(page_title,form_name)].append((cacao_property_aliases_func(key),sanitize_mediawiki_value(value_)))
        elif key in cacao_special_cases:
            for value_ in cacao_special_cases[key](value):
                shared_dict[(page_title,form_name)].append((cacao_property_aliases_func(key),sanitize_mediawiki_value(value_)))
        # Final case should only be either pure strings(ints, bools, etc) or lists of strings(ints, bools, etc)
        else:
            if isinstance(value,list):
                for v in value:
                    shared_dict[(page_title,form_name)].append((cacao_property_aliases_func(key),sanitize_mediawiki_value(v)))
            else:
                shared_dict[(page_title,form_name)].append((cacao_property_aliases_func(key),sanitize_mediawiki_value(value)))
    return shared_dict



convert_type_to_prop = {
    'InitialStep': 'hasInitialStep',
    'FinalStep': 'hasFinalStep',
    'IntermediateStep': 'hasIntermediateStep',
    'ExclusiveChoiceStep': 'hasExclusiveChoiceStep',
    'OptionalStep': 'hasOptionalStep',
    'Action': 'performAction',
    'Tool': 'useTool'
}


id_to_name = {'on_completion', 'on_true', 'on_false'}

action_equivalents = {
    # management
    '': ''
    # state preserving
    # state restoring
    # state changing
    # custom
    # meta
}

tlp_equivalents = {
    'TLP:RED': 'd - TLP:RED',
    'TLP:AMBER': 'c - TLP:AMBER',
    'TLP:GREEN': 'b - TLP:GREEN',
    'TLP:WHITE': 'a - TLP:WHITE',
}

def get_cacao_name(data:dict,id:str) -> str:
    """Returns either the name of a cacao object or its id if none is defined.

    Args:
        data (dict): The workflow dictionary
        id (str): The id of the object whose name is sought.

    Returns:
        str: Either the name or the id of the object.
    """
    if 'name' in data[id]:
        return data[id]['name'] + " id: " + id.split('--')[1]
    else:
        return id

def get_cacao_downstream_steps(data:dict,id:str) -> set:
    """Gets all downstream steps of step 'id' in the data dictionary. Including conditions and other nonsense.

    Args:
        data (dict): The workflow the steps are in
        id (str): The id of the step whose downstream is sought.

    Returns:
        set: Set of downstream steps
    """
    next_steps = set()
    if 'on_completion' in data[id]:
        next_steps.add(data[id]['on_completion'])
    if 'on_success' in data[id]:
        next_steps.add(data[id]['on_success'])
    if 'on_failure' in data[id]:
        next_steps.add(data[id]['on_failure'])
    if 'next_steps' in data[id]:
        next_steps.update(data[id]['next_steps'])
    if 'on_true' in data[id]:
        if isinstance(data[id]['on_true'],list):
            next_steps.update(data[id]['on_true'])
        elif isinstance(data[id]['on_true'],str):
            next_steps.add(data[id]['on_true'])
        else:
            raise TypeError("on_true is not a string or list")
    if 'on_false' in data[id] and data[id]['type'] == 'if-condition':
        if isinstance(data[id]['on_false'],list):
            next_steps.update(data[id]['on_false'])
        elif isinstance(data[id]['on_false'],str):
            next_steps.add(data[id]['on_false'])
        else:
            raise TypeError("on_false is not a string or list")
    if 'on_false' in data[id] and data[id]['type'] == 'while-condition':
        next_steps.add(data[id]['on_false'])
    if 'cases' in data[id]:
        for case in data[id]['cases'].values():
            if isinstance(case,list):
                next_steps.update(case)
            elif isinstance(case,str):
                next_steps.add(case)
            else:
                raise TypeError("case is not a string or list")
    return next_steps


def merge_list_dicts(dict_1:dict,dict_2:dict) -> dict:
    """Merges two dictionaries containing lists so that {key: [value1, value2]} and {key: [value3]} becomes {key: [value1, value2, value3]}

    Args:
        dict_1 (dict): The first dictionary
        dict_2 (dict): The second dictionary

    Returns:
        dict: The joined dictionary
    """
    new_dict = dict(**dict_1)
    for k in dict_2:
        if k in new_dict:
            new_dict[k] = new_dict[k] + dict_2[k]
        else:
            new_dict[k] = dict_2[k]
    return new_dict

def generate_action_id(data:dict,namespace:str="aa7caf3a-d55a-4e9a-b34e-056215fba56a") -> str:
    """Generates an id for an action.

    Args:
        data (dict): The dictionary containing the action(command)
        namespace (str): The namespace of the action. Default: "aa7caf3a-d55a-4e9a-b34e-056215fba56a"
    Returns:
        str: The generated id
    """
    json_string = json.dumps(data, sort_keys=True)
    uuid_string = str(uuid.uuid5(uuid.UUID(namespace), json_string))
    return "action-%s--%s" % (data['type'], uuid_string)

def gather_actions(workflow:dict) -> dict:
    """Gathers all actions in the workflow.

    Args:
        workflow (dict): The workflow

    Returns:
        dict: The dictionary of actions
    """
    actions = dict()
    for step_id in workflow:
        if 'type' in workflow[step_id] and workflow[step_id]['type'] == 'single':
            for command in workflow[step_id]['commands']:
                actions[generate_action_id(command)] = command
    return actions

def convert_workflow(workflow:dict,step_id:str,branch_stack:list=[],processed_steps:set=set()) -> dict:
    """Recursive function to convert a cacao workflow to a sappan playbook

    Args:
        workflow (dict): The workflow dictionary
        step_id (str): The id of the currently processed step. When calling should be the 'workflow_start' id
        branch_stack (list): Used to resolve branching steps like parallel and while-condition.
        processed_steps (set): Set of already processed steps. Should be empty on first call.

    Returns:
        dict: Returns a dictionary of the form {'step_type':list of steps}
    """
    converted_steps = dict()
    new_step = []
    next_steps = []
    end_steps = []

    if step_id in processed_steps:
        return converted_steps  # already processed
    else:
        processed_steps.add(step_id)

    # copy basic properties
    for k,v in workflow[step_id].items():
        if (k in step_prop_equivalents) and not (k in id_to_name) and not k=='name':
            new_step.append((step_prop_equivalents[k],v))
    new_step.append(('name',get_cacao_name(workflow,step_id)))
    
    for next_step_id in get_cacao_downstream_steps(workflow,step_id):
        # if we are currently off the main branch we have to reconsolidate the branch stack on end steps
        if branch_stack:
            if workflow[next_step_id]['type'] == 'end':
                end_steps.append(next_step_id)
            else:
                next_steps.append(next_step_id)
        # otherwise the end steps have no special treatment
        else:
            next_steps.append(next_step_id)
    
    # if we are currently off the main branch we have to reconsolidate the branch stack on end steps
    if end_steps:
        parent_step = branch_stack.pop()
        new_step.append(('hasNextStep',get_cacao_name(workflow,parent_step)))

    if workflow[step_id]['type'] == 'start':
        for next_step in next_steps:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        converted_steps.setdefault("InitialStep",[]).append(new_step)
        for step in next_steps:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack))
        return converted_steps
    
    if workflow[step_id]['type'] == 'end':
        converted_steps.setdefault("FinalStep",[]).append(new_step)
        return converted_steps
    
    if workflow[step_id]['type'] == 'single':
        for next_step in next_steps:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        if len(next_steps) <= 1:
            converted_steps.setdefault("IntermediateStep",[]).append(new_step)
        else:
            converted_steps.setdefault("ExclusiveChoiceStep",[]).append(new_step)
        
        # single action steps define commands TODO: add functionality
        for action in workflow[step_id]['commands']:
            new_step.append(('performAction',generate_action_id(action)))

        for step in next_steps:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack))
        return converted_steps
    
    if workflow[step_id]['type'] == 'playbook':
        for next_step in next_steps:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        
        # playbook gets added as action NOTE: this is not a real action
        new_step.append(('performAction',workflow[step_id]['playbook_id']))

        if len(next_steps) <= 1:
            converted_steps.setdefault("IntermediateStep",[]).append(new_step)
        else:
            converted_steps.setdefault("ExclusiveChoiceStep",[]).append(new_step)

        for step in next_steps:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack))
        return converted_steps

    if workflow[step_id]['type'] == 'parallel':
        for next_step in workflow[step_id]['next_steps']:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        converted_steps.setdefault("ExclusiveChoiceStep",[]).append(new_step)

        for step in workflow[step_id]['next_steps']:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack + [workflow[step_id]['on_completion']]))
        return converted_steps

    if workflow[step_id]['type'] == 'if-condition':
        for next_step in next_steps:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        converted_steps.setdefault("ExclusiveChoiceStep",[]).append(new_step)
        # if steps define conditions TODO: add functionality

        for step in next_steps:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack))
        return converted_steps
    
    if workflow[step_id]['type'] == 'while-condition':
        for next_step in next_steps:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        converted_steps.setdefault("ExclusiveChoiceStep",[]).append(new_step)
        # while steps define conditions TODO: add functionality

        for step in workflow[step_id]['on_true']:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack+[step_id]))
        converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,workflow[step_id]['on_false'],branch_stack))
        return converted_steps
    
    if workflow[step_id]['type'] == 'switch-condition':
        for next_step in next_steps:
            new_step.append(('hasNextStep',get_cacao_name(workflow,next_step)))
        converted_steps.setdefault("ExclusiveChoiceStep",[]).append(new_step)
        # switch steps define conditions TODO: add functionality

        for step in next_steps:
            converted_steps = merge_list_dicts(converted_steps,convert_workflow(workflow,step,branch_stack))
        return converted_steps
