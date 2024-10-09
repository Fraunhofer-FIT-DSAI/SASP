import logging

from .utils import wiki_name
from sasp.bpmn import BPMN

logger = logging.getLogger(__name__)

def generate_bpmn_cacao_1_1(playbook_db):
    """
    New version of the BPMN generation function for CACAO Playbooks.

    Args:
        playbook_db (Playbook): Django model db object of the playbook
        playbook_objects_db (QuerySet): Django queryset of the playbook objects
    """
    import sasp.models.cacao_1_1 as cacao
    
    playbook_db = playbook_db.resolve_subclass()

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
            bpmn_events[step.wiki_page_name] = BPMN.StartEvent(name=step.get_name(), id=step.wiki_page_name)
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