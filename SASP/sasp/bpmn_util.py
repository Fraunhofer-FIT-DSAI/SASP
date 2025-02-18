import logging

from .utils import wiki_name
from sasp.bpmn import BPMN
from sasp.knowledge import BPMN as bpmn_knowledge

logger = logging.getLogger(__name__)

def generate_bpmn_cacao_1_1_automation(automation_db):
    """
    New version of the BPMN generation function for CACAO Playbooks.

    Args:
        automation_db (Automation): Django model db object of the automation
    """
    playbook_objects = automation_db.playbook_frozen
    playbook_objects = {key: value for key, value in playbook_objects.items()}

    error_list = list()
    bpmn_xml = None
    
    bpmn_events = dict()
    bpmn_obj = BPMN()
    
    # Populate events
    for step in playbook_objects.values():
        if step['bpmn_type'] == 'start_event':
            bpmn_events[step['id']] = BPMN.StartEvent(
                name=step['name'], 
                id=step['id']
            )
        elif step['bpmn_type'] == 'end_event':
            bpmn_events[step['id']] = BPMN.EndEvent(
                name=step['name'], 
                id=step['id']
            )
        elif step['bpmn_type'] == 'task':
            bpmn_events[step['id']] = BPMN.Task(
                name=step['name'], 
                id=step['id']
            )
        elif step['bpmn_type'] == 'parallel_gateway':
            bpmn_events[step['id']] = BPMN.ParallelGateway(
                name=step['name'], 
                id=step['id']
            )
        elif step['bpmn_type'] == 'exclusive_gateway':
            bpmn_events[step['id']] = BPMN.ExclusiveGateway(
                name=step['name'], 
                id=step['id']
            )
        elif step['bpmn_type'] == 'inclusive_gateway':
            bpmn_events[step['id']] = BPMN.InclusiveGateway(
                name=step['name'], 
                id=step['id']
            )
        else:
            error_list.append(f"Step {step['id']} has an invalid form")
            return bpmn_xml, error_list
    
    # Register events
    for event in bpmn_events.values():
        bpmn_obj.process.add_element(event)
    
    pass
    # Populate connections
    for step in playbook_objects.values():
        outgoing = step['outgoing']
        if not outgoing:
            continue
        # Workflow Steps
        for connection,next_step in outgoing:
            if next_step not in bpmn_events:
                if wiki_name(next_step) in playbook_objects:
                    next_step = wiki_name(next_step)
                else:
                    error_list.append(f"'{step}' -> '{next_step}': Step '{next_step}' not found")
                    continue
            
            bpmn_events[f"{step['id']}_{next_step}"] = BPMN.SequenceFlow(
                id=f"{step['id']}_{next_step}",
                source=bpmn_events[step['id']],
                target=bpmn_events[next_step],
                process=bpmn_obj.process,
                name=connection,
            )
    
    # Colorize the BPMN diagram according to state of execution
    objects_state = automation_db.objects_state
    # colors
    
    # INITIALIZED = "Initialized"
    # RUNNING = "Running"
    # FAILED = "Failed"
    # SUCCEEDED = "Succeeded"
    
    for event in bpmn_events.values():
        if isinstance(event, BPMN.SequenceFlow):
            if objects_state.get(event.id, None) == 'Walked':
                event.border_color = bpmn_knowledge.walked_edge_color
            else:
                event.border_color = bpmn_knowledge.unmarked_edge_color
        elif event.id in objects_state:
            if objects_state[event.id] == 'Succeeded':
                event.border_color = bpmn_knowledge.success_color_border
                event.background_color = bpmn_knowledge.success_color
            elif objects_state[event.id] == 'Running':
                event.border_color = bpmn_knowledge.in_progress_color_border
                event.background_color = bpmn_knowledge.in_progress_color
            elif objects_state[event.id] == 'Failed':
                event.border_color = bpmn_knowledge.failed_color_border
                event.background_color = bpmn_knowledge.failed_color
            elif objects_state[event.id] == 'Initialized':
                event.border_color = bpmn_knowledge.initialized_color_border
                event.background_color = bpmn_knowledge.initatialized_color
            elif objects_state[event.id] == 'Active':
                event.border_color = bpmn_knowledge.active_color_border
                event.background_color = bpmn_knowledge.active_color
            else:
                event.border_color = bpmn_knowledge.default_color_border
                event.background_color = bpmn_knowledge.default_color
    
    bpmn_obj.layout(orientation='horizontal')
    bpmn_xml = bpmn_obj.xml()
    return bpmn_xml, error_list

def generate_bpmn_cacao_1_1(playbook_db):
    """
    New version of the BPMN generation function for CACAO Playbooks.

    Args:
        playbook_db (Playbook): Django model db object of the playbook
        playbook_objects_db (QuerySet): Django queryset of the playbook objects
    """
    import sasp.models.cacao_1_1 as cacao
    
    playbook_db:cacao.CACAO_1_1 = playbook_db.resolve_subclass()

    playbook_objects = playbook_db.playbook_objects.all()
    playbook_objects = [obj.resolve_subclass() for obj in playbook_objects]
    playbook_steps = {obj.wiki_page_name: obj for obj in playbook_objects if isinstance(obj, cacao.CACAO_1_1_Step_Object)}
    playbook_objects = {obj.wiki_page_name: obj for obj in playbook_objects}

    error_list = list()
    bpmn_xml = None
    
    bpmn_events = dict()
    bpmn_obj = BPMN()
    
    # Populate events
    for step in playbook_steps.values():
        if isinstance(step, cacao.CACAO_1_1_StartStep):
            bpmn_events[step.wiki_page_name] = BPMN.StartEvent(
                name=step.get_name(), 
                id=step.wiki_page_name
            )
        elif isinstance(step, cacao.CACAO_1_1_EndStep):
            bpmn_events[step.wiki_page_name] = BPMN.EndEvent(name=step.get_name(), id=step.wiki_page_name)
        elif isinstance(step, cacao.CACAO_1_1_SingleActionStep):
            bpmn_events[step.wiki_page_name] = BPMN.Task(name=step.get_name(), id=step.wiki_page_name)
        elif isinstance(step, cacao.CACAO_1_1_PlaybookStep):
            bpmn_events[step.wiki_page_name] = BPMN.Task(name=step.get_name(), id=step.wiki_page_name)
        elif isinstance(step, cacao.CACAO_1_1_ParallelStep):
            bpmn_events[step.wiki_page_name] = BPMN.ParallelGateway(name=step.get_name(), id=step.wiki_page_name)
        elif isinstance(step, cacao.CACAO_1_1_IfConditionStep):
            bpmn_events[step.wiki_page_name] = BPMN.ExclusiveGateway(name=step.get_name(), id=step.wiki_page_name)
        elif isinstance(step, cacao.CACAO_1_1_WhileConditionStep):
            bpmn_events[step.wiki_page_name] = BPMN.ExclusiveGateway(name=step.get_name(), id=step.wiki_page_name)
        elif isinstance(step, cacao.CACAO_1_1_SwitchConditionStep):
            bpmn_events[step.wiki_page_name] = BPMN.InclusiveGateway(name=step.get_name(), id=step.wiki_page_name)
        else:
            error_list.append(f"Step {step.wiki_page_name} has an invalid form")
            return bpmn_xml, error_list
    
    # Register events
    for event in bpmn_events.values():
        bpmn_obj.process.add_element(event)
    
    pass
    # Populate connections
    for step in playbook_steps.values():
        next_objects = step.get_next_objects()
        if not next_objects:
            continue
        # Workflow Steps
        for connection in next_objects['Workflow Step']:
            for next_step in next_objects['Workflow Step'][connection]:
                if next_step not in bpmn_events:
                    if wiki_name(next_step) in playbook_objects:
                        next_step = wiki_name(next_step)
                    else:
                        error_list.append(f"'{step}' -> '{next_step}': Step '{next_step}' not found")
                        continue
                
                BPMN.SequenceFlow(
                    source=bpmn_events[step.wiki_page_name],
                    target=bpmn_events[next_step],
                    process=bpmn_obj.process,
                    name=connection,
                )
    
    bpmn_obj.layout(orientation='horizontal')
    bpmn_xml = bpmn_obj.xml()
    return bpmn_xml, error_list