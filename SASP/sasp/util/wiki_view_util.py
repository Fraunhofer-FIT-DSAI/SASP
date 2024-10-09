import re
import os
import itertools
import webbrowser

import sasp.knowledge as knowledge
from util.object_alter_util import get_instance_info_wide
from interface.tree_views import TreeViewEntryInstance
import logging

logger = logging.getLogger(__name__)


def get_template_variables(site, template_name):
    """Retrieve variable names from the class of an object used for defining
    what a class is.

    Args:
        site (Site): Wiki instance
        template_name (str): Name of the object class template on the wiki

    Returns:
        List[str]: Variable names of the object class
    """
    # isolate the template
    t = site.pages[f'Template:{template_name}'].text().split('/noinclude>')[0]
    t = t.split(':')[1]
    t = [re.sub(r'[^\w]', '', prop.split(' (')[0]) for prop in t.split('|')]

    return t


def get_form_variables(site, form_name):
    """Retrieve variable names of an object class from the form documents
    on the wiki. The form contains more information as opposed to the template.

    Args:
        site (Site): Wiki instance
        form_name (str): Name of the object class form on the wiki

    Returns:
        List[Tuple[str, str]]: List of variable names and types
    """
    t = site.pages[f'Form:{form_name}'].text().split('{{{field')[1:]

    t = [var.split('}}}')[:-1] for var in t]

    flattened_t = list(itertools.chain.from_iterable(t))
    variables = []
    for pair in flattened_t:
        if 'type=' in pair:
            t2 = pair.split('|')[1:]
            var_name = t2[0]
            var_type = t2[1].split('=')[1]
            variables.append((var_name, var_type))

    return variables

def get_page_categories(site, page):
    """Get a list of categories that a page is associated with.

    Args:
        site (Site): Wiki instance
        page (str): Name of the page to get the categories from
    """
    category_names = []
    for c in site.pages[page].categories():
        category_names.append(c.name)
    return category_names

def get_list_of_instances(site, category):
    """Get list of instances in a particular category.

    Args:
        site (Site): Wiki instance
        category (str): Category to retrieve the instances from

    Returns:
        List[str]: Names of the instances associated to the category
    """
    instances = site.categories[category]
    return [i.name for i in instances if i.namespace == 0]


def get_list_of_categories(site):
    """Get the list of categories that are present in the wiki.

    Args:
        site (Site): Wiki instance

    Returns:
        List[str]: List of category names hosted on the wiki
    """
    return sorted([c.name.split(':')[1] for c in site.allcategories()])


def get_category_page(site, category):
    """Get the Page instance of a particular category from the wiki.

    Args:
        site (Site): Wiki instance
        category (str): Category name

    Returns:
        Page: Page instance of the wiki
    """
    return site.categories[category]


def open_wiki_instance(title):
    """Opens the default browser and directs a new tab to the input page title.

    Args:
        title (str): Name of the page to open
    """
    webbrowser.open(f'{os.getenv("USER_URL")}{title}', new=2)


def open_bpmn_link(title):
    """Opens the default browser and directs a new tab to the input bpmn page.

    Args:
        title (str): Name of the BPMN page to open
    """
    link = f'{os.getenv("API")}index.php?title=BPMN:{title}&action=editdiagram'
    webbrowser.open(link, new=2)


def get_instance_objects(site, form, name):
    """Retrieves any page that is directly linked to the input playbook. With
    the page names, create list of all the objects directly linked along with
    how they are linked.

    Args:
        site (Site): Wiki instance
        form (str): form name to get the objects from
        name (str): Name of the playbook to fetch linked page names

    Returns:
        List[str]: List description of all attached pages to the playbook
    """
    form_var = dict(get_form_variables(site, form))
    accepted_prop = {k for k in form_var
                     if form_var[k] == 'tokens' or 'Step' in k}
    instance_prop = get_instance_info_wide(site, name)
    return [f'{p}/{v}' for p, v in instance_prop if p in accepted_prop]


def get_instance_objects_all(site, name, new_mode=False):
    """Iteratively go through the tree with input page name as the root in
    order to fetch all of the pages that branch down from the root.

    Args:
        site (Site): Wiki instance
        name (str): Name of the page that acts as the root
        new_mode (bool): If True, will return a list of dictionaries instead of merged strings

    Returns:
        List[str]: List of all the pages down the tree
    """
    if not new_mode:
        logger.warning("get_instance_objects_all is called with new_mode=False. This is deprecated and will be removed in the future.")
        all_links = [name]
    else:
        all_links = [
            {
                'name': name, 
                'type': 'root', 
                'parent': None,
                'page_name': name
            }
        ]
    new_links = list(site.pages[name].links())
    seen_links = {x.name for x in new_links}
    while new_links:
        old_links = new_links
        new_links = []
        for link in old_links:
            l_name = link.name
            if link.exists:
                try:
                    link_categories = list(link.categories())
                    l_type = link_categories[0]
                    l_type = l_type.name.split(':',1)[1]
                    if l_type not in knowledge.PLAYBOOK_CATEGORIES:
                        new_links += [x for x in link.links()
                                    if x.name not in seen_links]
                        seen_links.add(l_name)
                        if new_mode:
                            all_links.append(
                                {   'name': l_name.split(':',1)[1] if ':' in l_name else l_name,
                                    'type': l_type, 
                                    'parent': l_name.split(':',1)[0] if ':' in l_name else None,
                                    'page_name': l_name
                                }
                            )
                        else:
                            all_links.append(f'{l_type}/{l_name}')
                            link_str = f'{l_type}/{l_name}'
                            all_links.append(link_str)
                except IndexError:
                    pass
                except Exception as e:
                    raise e
    if new_mode:
        all_links_new = []
        for link in all_links:
            all_links_new.append(
                TreeViewEntryInstance(
                    name = link['name'],
                    page_name = link['page_name'],
                    form_name = link['type'],
                    parent_page = link['parent']
                )
            )
        return all_links_new

    return all_links


def get_all_namespace_instances(site, namespace):
    """Get a list of pages that exist in a wiki namespace. A wiki namespace
    is a specific prefix separated with a colon which organizes the wiki. For
    example the namespace BPMN: contains all of the bpmn diagrams that exist
    on the wiki and are viewable by the user.

    Args:
        site (Site): Wiki instance
        namespace (str): Name of the namespace without the colon

    Returns:
        List[str]: List of all the pages associated in the namespace
    """
    namespace_int = 0
    for ns_int, ns_name in site.namespaces.items():
        if ns_name == namespace:
            namespace_int = ns_int
    return [p.name.split(f'{namespace}:')[1]
            for p in site.allpages(namespace=f'{namespace_int}')]

def get_page_form(site, page):
    """Get the associated form name of a page.

    Args:
        site (Site): Wiki instance
        page (str): Name of the page to get the form from

    Returns:
        str: Name of the form associated to the page
    """
    for category in get_page_categories(site,page):
        form_name = category.replace('Category:','Form:',1)
        if site.pages[form_name].exists:
            return form_name.replace('Form:','')
    return None
