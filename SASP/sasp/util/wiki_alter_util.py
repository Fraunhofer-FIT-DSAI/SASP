from util.object_alter_util import create_instance_query
from util.wiki_view_util import get_form_variables
import logging
import sasp.knowledge as knowledge

logger = logging.getLogger(__name__)

def create_form(site, form, title, playbook_name=None):
    """Creates an instance of an object (a new page) on the wiki based on the
    form and title. This is the initial creation where all values are empty
    (other than default values). If the page already exists, it does nothing.

    Args:
        site (Site): Wiki instance
        form (str): Name of the form that is used for the type of object
        title (str): Name of the new object/page
    """
    page = site.pages[title]
    template = form.replace(' ', '')
    query = create_instance_query([(k, '') for k, _ in
                                   get_form_variables(site, form)],
                                  template)

    if form in knowledge.PLAYBOOK_CATEGORIES:
        query = f'{query}&pf_free_text={{{{#display_diagram:BPMN:{title}}}}}'
        bpmn_page = site.pages[f'BPMN:{title}']
        bpmn_page.edit(' ', 'Created BPMN!')
    elif playbook_name and 'Step' in form:
        query = f'{query}&{template}[isStepOf]={playbook_name}'

    if not page.exists:
        site.api('pfautoedit', form=form, target=title, query=query)


def create_form_import(site, form, title, prop_list,reset_page=False):
    """Creates an instance of an object (a new page) on the wiki based on the
    form, title and a set of properties. This is called when a new playbook
    is being imported into the system.

    Args:
        site (Site): Wiki instance
        form (str): Name of the form that is used for the type of the object
        title (str): Name of the new object/page
        prop_list (List[Tuple[str, str]]): Wide propety list of the instance
        reset_page (bool): If true, the page is reset before the import
    """
    if reset_page:
        logger.debug("Resetting page '{}'".format(title))
        page = site.pages[title]
        page.edit('', 'Resetting page')
    logger.debug("Creating query for instance '{}' with form '{}'".format(title, form))
    query = create_instance_query(prop_list, form.replace(' ', '_'))
    if form in knowledge.PLAYBOOK_CATEGORIES:
        query = f'{query}&pf_free_text={{{{#display_diagram:BPMN:{title}}}}}'
        bpmn_page = site.pages[f'BPMN:{title}']
        bpmn_page.edit(' ', 'Created BPMN!')

    logger.debug('form, title, query\n%s, %s, %s',form, title, query)
    site.api('pfautoedit', form=form, target=title, query=query)


def update_playbook(site, name, form, changes):
    """Update the specified instance with new information.

    Args:
        site (Site): Wiki instance
        name (str): Name of the instance to update
        form (str): Name of the form that is used for the type of the object
        changes (List[Tuple[str, str]]): Predicate and object changes to be
        made to the instance
    """
    page = site.pages[name]
    if page.exists:
        new_query = create_instance_query(changes, form.replace(' ', '_'))
        logger.debug('new_query:\n%s',new_query)
        response = site.api('pfautoedit', form=form, target=name, query=new_query)
        logger.debug("update_playbook response:\n%s",response)
    else:
        logger.info('page does not exist.')


def delete_wiki_object(site, instance):
    """Delete an instance/page from the wiki.

    Args:
        site (Site): Wiki instance
        instance (str): The name of the page that the user wants to delete
    """
    response = site.pages[instance].delete(reason='Removed from app.')
    logger.debug("delete_wiki_object response:\n%s",response)
