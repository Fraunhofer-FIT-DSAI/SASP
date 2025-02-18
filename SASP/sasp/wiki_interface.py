import sasp.knowledge as knowledge
from .utils import wiki_name
from mwclient import Site
import sasp.models
from sasp.models.auth import UserProfile

import logging
import requests
import os
import re
import itertools
import webbrowser
from time import mktime
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

class Wiki:
    # def __new__(cls):
    #     """Override __new__ to make this a singleton class"""
    #     if not hasattr(cls, 'instance'):
    #         cls.instance = super(Wiki, cls).__new__(cls)
    #     return cls.instance
    logger = logging.getLogger(__name__)
    jinja = Environment(
        loader=FileSystemLoader(
            Path(__file__).parent / 'templates' / 'wikitext'
        ), 
        lstrip_blocks=True, 
        trim_blocks=True
    )
    kb = knowledge.KnowledgeBase()
    site: Site = None
    connected: bool = None
    
    @classmethod
    def connect(cls, url, path, username, password) -> bool:
        try:
            cls.site = Site(
                url.split('//')[1],
                scheme=url.split('://')[0],
                path=path,
            )
            cls.site.login(username, password)
            cls.site.force_login = False
            cls.connected = True
            return True
        except requests.exceptions.ConnectionError:
            cls.logger.warning("Could not connect to wiki, check your settings")
            cls.site = None
            cls.connected = False
            return False

    """Read-only functions for the wiki"""

    def _get_template_variables(self, template_name):
        """Retrieve variable names from the class of an object used for defining
        what a class is.

        Args:
            template_name (str): Name of the object class template on the wiki

        Returns:
            List[str]: Variable names of the object class
        """
        # isolate the template
        t = self.site.pages[f'Template:{template_name}'].text().split('/noinclude>')[0]
        t = t.split(':')[1]
        t = [re.sub(r'[^\w]', '', prop.split(' (')[0]) for prop in t.split('|')]

        return t

    def _get_template_info(self, template_name, include_source=False, source=None):
        """Retrieve variable names from the class of an object used for defining
        what a class is.

        Args:
            template_name (str): Name of the object class template on the wiki (without 'Template:' prefix)
            include_source (bool, optional): Whether to include the source of the template. Defaults to False.
            source (str, optional): Source code of the template. To avoid fetching from wiki. Defaults to None.

        Returns:
            Dict[str, dict]|None,: Dictionary of variable names and their properties, None if template doesn't exist
            str(Optional): Source of the template (if include_source is True)
        """
        if source is None:
            source = self.site.pages[f'Template:{template_name}']
            if not source.exists:
                return None
            source = source.text()

        template_params = re.search("{{#template_params:(.*?)}}", source)
        if template_params is None:
            print("DEBUG (_get_template_info): Regex failed, template params not found")
            return {}
        template_params = template_params.group(1) # type (label=Type;property=type)|...
        template_params = template_params.split("|") # [type (label=Type;property=type), ...]

        template_table = re.search(r'{\| class="wikitable"(.*?)\|}\s*\[\[', source, re.DOTALL)
        if template_table is None:
            self.logger.debug("DEBUG (_get_template_info): Regex failed, template table not found")
            return {}
        template_table = template_table.group(1) # ! Label \n| ...
        template_table_dict = {}
        for match in re.finditer(r"! (.*?)\n\|(.*?)\n", template_table):
            label = match.group(1).strip()
            template_table_dict[label] = {"list" : False}
            if "#arraymap:" in match.group(2):
                template_table_dict[label]["list"] = True
                seperator = re.search(r"}\|(.)\|", match.group(2))
                try:
                    seperator = seperator.group(1)
                except Exception as e:
                    # Shouldn't happen, but wiki syntax is weird
                    print(f"Error parsing seperator for {template_name} {label}")
                    raise e
                template_table_dict[label]["seperator"] = seperator


        template_info = {}
        for i,param in enumerate(template_params):
            # type (label=Type;property=type)
            field_name = param.split("(")[0].strip() # type
            param_properties = "(" + param.split("(", 1)[1] # (label=Type;property=type)
            param_properties = param_properties.strip()[1:-1] # label=Type;property=type
            param_properties = param_properties.split(";") # [label=Type, property=type]
            param_properties_dict = {}
            for prop in param_properties:
                if "=" in prop:
                    if len(prop.split("=")) != 2:
                        print("DEBUG (_get_template_info): Pattern matching failed")
                        raise Exception("Pattern matching failed")
                    prop_name, prop_value = prop.split("=")
                    param_properties_dict[prop_name] = prop_value
                else:
                    param_properties_dict[prop] = True
            param_properties = param_properties_dict
            del param_properties_dict

            # If the field is a list, info is in second part of source
            label = param_properties["label"]
            param_properties["index"] = i
            if template_table_dict[label]["list"]:
                param_properties["list"] = template_table_dict[label]["seperator"]
            
            template_info[field_name] = param_properties
        
        if include_source:
            return template_info, source
        else:
            return template_info

    def _get_form_variables(self, form_name, source=None):
        """Retrieve variable names of an object class from the form documents
        on the wiki. The form contains more information as opposed to the template.

        Args:
            form_name (str): Name of the object class form on the wiki
            source (str, optional): Source code of the form. To avoid fetching from wiki. Defaults to None.

        Returns:
            List[Tuple[str, str]]: List of variable names and types
        """
        if source is None:
            source = self.site.pages[f'Form:{form_name}'].text()
        t = source.split('{{{field')[1:]

        t = [var.split('}}}')[:-1] for var in t]

        flattened_t = list(itertools.chain.from_iterable(t))
        variables = []
        for pair in flattened_t:
            if 'type=' in pair:
                t2 = pair.split('|')[1:]
                var_name = t2[0]
                var_type = t2[1].split('=')[1]
                variables.append((var_name.strip(), var_type.strip()))

        return variables

    def _get_page_categories(self, page):
        """Get a list of categories that a page is associated with.

        Args:
            page (str): Name of the page to get the categories from
        """
        category_names = []
        for c in self.site.pages[page].categories():
            category_names.append(c.name)
        return category_names

    def _get_list_of_instances(self, category):
        """Get list of instances in a particular category.

        Args:
            site (Site): Wiki instance
            category (str): Category to retrieve the instances from

        Returns:
            List[str]: Names of the instances associated to the category
        """
        instances = self.site.categories[category]
        return [i.name for i in instances if i.namespace == 0]


    def _get_list_of_categories(self):
        """Get the list of categories that are present in the wiki.

        Args:

        Returns:
            List[str]: List of category names hosted on the wiki
        """
        return sorted([c.name.split(':')[1] for c in self.site.allcategories()])


    def _get_category_page(self, category):
        """Get the Page instance of a particular category from the wiki.

        Args:
            category (str): Category name

        Returns:
            Page: Page instance of the wiki
        """
        return self.site.categories[category]


    def _open_wiki_instance(title):
        """Opens the default browser and directs a new tab to the input page title.

        Args:
            title (str): Name of the page to open
        """
        webbrowser.open(f'{os.getenv("USER_URL")}{title}', new=2)


    def _open_bpmn_link(title):
        """Opens the default browser and directs a new tab to the input bpmn page.

        Args:
            title (str): Name of the BPMN page to open
        """
        link = f'{os.getenv("API")}index.php?title=BPMN:{title}&action=editdiagram'
        webbrowser.open(link, new=2)


    def _get_instance_objects(self, form, name):
        """Retrieves any page that is directly linked to the input playbook. With
        the page names, create list of all the objects directly linked along with
        how they are linked.

        Args:
            form (str): form name to get the objects from
            name (str): Name of the playbook to fetch linked page names

        Returns:
            List[str]: List description of all attached pages to the playbook
        """
        form_var = dict(self._get_form_variables(form))
        accepted_prop = {k for k in form_var
                        if form_var[k] == 'tokens' or 'Step' in k}
        instance_prop = self._get_instance_info_wide(name)
        return [f'{p}/{v}' for p, v in instance_prop if p in accepted_prop]


    def _get_instance_objects_all(self, name, new_mode=False):
        """Iteratively go through the tree with input page name as the root in
        order to fetch all of the pages that branch down from the root.

        Args:
            name (str): Name of the page that acts as the root
            new_mode (bool): If True, will return a list of dictionaries instead of merged strings

        Returns:
            List[str]: List of all the pages down the tree
        """
        if not new_mode:
            self.logger.warning("get_instance_objects_all is called with new_mode=False. This is deprecated and will be removed in the future.")
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
        new_links = list(self.site.pages[name].links())
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
            return {
                        link['page_name']: 
                            {
                                'name' : link['name'],
                                'page_name' : link['page_name'],
                                'form_name' : link['type'],
                                'parent_page' : link['parent']
                            } for link in all_links
                    }

        return all_links


    def _get_all_namespace_instances(self, namespace):
        """Get a list of pages that exist in a wiki namespace. A wiki namespace
        is a specific prefix separated with a colon which organizes the wiki. For
        example the namespace BPMN: contains all of the bpmn diagrams that exist
        on the wiki and are viewable by the user.

        Args:
            namespace (str): Name of the namespace without the colon

        Returns:
            List[str]: List of all the pages associated in the namespace
        """
        namespace_int = 0
        for ns_int, ns_name in self.site.namespaces.items():
            if ns_name == namespace:
                namespace_int = ns_int
        return [p.name.split(f'{namespace}:')[1]
                for p in self.site.allpages(namespace=f'{namespace_int}')]

    def _get_page_form(self, page):
        """Get the associated form name of a page.

        Args:
            page (str): Name of the page to get the form from

        Returns:
            str: Name of the form associated to the page
        """
        for category in self._get_page_categories(page):
            form_name = category.replace('Category:','Form:',1)
            if self.site.pages[form_name].exists:
                return form_name.replace('Form:','')
        return None

    """Write Functions for Wiki"""
    def _create_form(self, form, title, playbook_name=None):
        """Creates an instance of an object (a new page) on the wiki based on the
        form and title. This is the initial creation where all values are empty
        (other than default values). If the page already exists, it does nothing.

        Args:
            form (str): Name of the form that is used for the type of object
            title (str): Name of the new object/page
        """
        page = self.site.pages[title]
        template = form.replace(' ', '')
        query = self._create_instance_query([(k, '') for k, _ in
                                    self._get_form_variables(form)],
                                    template)

        if form in knowledge.PLAYBOOK_CATEGORIES:
            query = f'{query}&pf_free_text={{{{#display_diagram:BPMN:{title}}}}}'
            bpmn_page = self.site.pages[f'BPMN:{title}']
            bpmn_page.edit(' ', 'Created BPMN!')
        elif playbook_name and 'Step' in form:
            query = f'{query}&{template}[isStepOf]={playbook_name}'

        if not page.exists:
            self.site.api('pfautoedit', form=form, target=title, query=query)
    
    def _edit_from_source(self, title, source, comment="Automated edit"):
        """Edits or creates a page on the wiki based on the title and source.

        Args:
            title (str): Name of the page to edit (including namespace)
            source (str): Source code of the page
            comment (str): Comment to add to the edit
        """
        page = self.site.pages[title]
        page.edit(source, comment)


    def _create_form_import(self, form, title, prop_list,reset_page=False):
        """Creates an instance of an object (a new page) on the wiki based on the
        form, title and a set of properties. This is called when a new playbook
        is being imported into the system.

        Args:
            form (str): Name of the form that is used for the type of the object
            title (str): Name of the new object/page
            prop_list (List[Tuple[str, str]]): Wide propety list of the instance
            reset_page (bool): If true, the page is reset before the import
        """
        if reset_page:
            self.logger.debug("Resetting page '{}'".format(title))
            page = self.site.pages[title]
            page.edit('', 'Resetting page')
        self.logger.debug("Creating query for instance '{}' with form '{}'".format(title, form))
        query = self._create_instance_query(prop_list, form.replace(' ', '_'))
        if form in knowledge.PLAYBOOK_CATEGORIES:
            query = f'{query}&pf_free_text={{{{#display_diagram:BPMN:{title}}}}}'
            bpmn_page = self.site.pages[f'BPMN:{title}']
            bpmn_page.edit(' ', 'Created BPMN!')

        self.logger.debug('form, title, query\n%s, %s, %s',form, title, query)
        self.site.api('pfautoedit', form=form, target=title, query=query)


    def _update_playbook(self, name, form, changes):
        """Update the specified instance with new information.

        Args:
            name (str): Name of the instance to update
            form (str): Name of the form that is used for the type of the object
            changes (List[Tuple[str, str]]): Predicate and object changes to be
            made to the instance
        """
        page = self.site.pages[name]
        if page.exists:
            new_query = self._create_instance_query(changes, form.replace(' ', '_'))
            self.logger.debug('new_query:\n%s',new_query)
            response = self.site.api('pfautoedit', form=form, target=name, query=new_query)
            self.logger.debug("update_playbook response:\n%s",response)
        else:
            self.logger.info('page does not exist.')


    def _delete_wiki_object(self, instance):
        """Delete an instance/page from the wiki.

        Args:
            instance (str): The name of the page that the user wants to delete
        """
        page = self.site.pages[instance]
        if page.exists:
            response = self.site.pages[instance].delete(reason='Removed from app.')
            self.logger.debug("delete_wiki_object response:\n%s",response)
        else:
            self.logger.info(f'Delete failed. Page {instance} does not exist.')
    
    """Functions from object_alter_util"""
    def _get_instance_info(self, name):
        """Retrieves all the instance (eg. playbook) information from the wiki in
        a psuedo RDF triple format List[(name, instance_info[0], instance_info[1])]

        Args:
            name (str): Name of the instance to get the information from

        Returns:
            List[Tuple[str, str]]: Predicates and Objects of the triples.
        """
        self.logger.debug(f'Getting instance info for "{name}"')
        t = self._custom_get_page_text(name)
        if t is None:
            self.logger.error(f'Error getting instance info for "{name}". Page probably doesn\'t exist.')
            return None
        if t == '':
            self.logger.error(f'Error getting instance info for "{name}". Page is empty.')
            self.logger.warning(
                'There is a known issue where the api returns an empty string for a page that exists.\n' +
                'Please report this issue to the developers.'
            )
            return []
        # isolate the instance info
        try:
            t = t.split('{{',1)[1]
            t = t.split('}}',1)[0]
        except Exception as e:
            self.logger.error(f'Error getting instance info for "{name}"')
            self.logger.error(e)
            raise e

        # split the instance info into predicates and objects
        entries = {prop.strip():values.strip() for prop,values in [x.split('=',1) for x in t.split('|')[1:]]}
        instance_info = []
        for prop,values in entries.items():
            instance_info.append((prop, values))
        return instance_info


    def _get_instance_info_wide(self, name):
        """Retrieves all the instance (eg. playbook) information from the wiki in
        a psuedo RDF triple format. The wide format splits any multiple token line
        into each its own predicate and object tuple.

        Args:
            site (Site): Wiki instance
            name (str): Name of the instance to get the information from

        Returns:
            List[Tuple[str, str]]: Predicates and Objects of the triples.
        """
        page_info = self._get_instance_info(name)
        page_prop_tuples = []


        try:
            for prop, value in page_info:
                if ',' in value and prop.lower() not in knowledge.FREE_TEXT_FIELDS:
                    page_prop_tuples.extend([(prop, value_.strip()) for value_ in value.split(',')])
                else:
                    page_prop_tuples.append((prop, value))
        except Exception as e:
            self.logger.error(f'Error getting instance info for {name}')
            self.logger.error(e)
            raise e

        return page_prop_tuples


    def _wide_tup_list_to_dict(self,instance_tups):
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

    """New functions for web app"""

    def _get_page_text(self, page_name):
        """Return the text of the page or None if the page does not exist"""
        page = self.site.pages[page_name]
        if page.exists:
            return page.text()
        else:
            return None
    
    def _custom_get_page_text(self, page_name):
        # Since switching to the new mw version, the mwclient method has been seemingly randomly failing
        # This is a quick fix that I have a feeling will remain here for a long time even though it
        # really shouldn't
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'revisions',
            'titles': page_name,
            'rvprop': 'content',
            'rvslots': 'main',
            'formatversion': '2'
        }
        response = requests.get(self.kb.wiki_api_url + 'api.php', params=params)
        response = response.json()
        try:
            if response['query']['pages'][0].get('missing', False):
                return None
            return response['query']['pages'][0]['revisions'][0]['slots']['main']['content']
        except Exception as e:
            self.logger.error(f"Error fetching page text for {page_name}")
            self.logger.error(e)
            return None
    
    def get_playbooks_ask(self):        
        """Uses the ask query to fetch all playbooks. This is more reliable than the previous method."""
        query = (
            "OR".join(f"[[Category:{category}]]" for category in knowledge.PLAYBOOK_CATEGORIES) +
            "|?Category"
        )
        response = self.site.api('ask', query=query)
        try:
            playbook_dict = dict()
            for page_name,result in response['query']['results'].items():
                entry = {
                    "name" : result["fulltext"],
                    "page_name" : result["fulltext"],
                    "url" : result["fullurl"]
                }
                # ["printouts"]["Category"]list["fulltext"] == "Category:?"
                forms = [form["fulltext"][9:] for form in result["printouts"]["Category"] if form["fulltext"][9:] in knowledge.PLAYBOOK_CATEGORIES]
                if len(forms)!=1:
                    self.logger.error(f"Error fetching form for {page_name}")
                    continue
                entry["form"] = forms[0]
                playbook_dict[page_name] = entry
            return playbook_dict
        except Exception as e:
            self.logger.error("Error getting page %s",page_name)
            self.logger.error("Response: %s",response)
            raise e
    
    def get_pages_by_form(self, form):
        """Return page names of all pages with the given form. (The form name is expected to be the same as the template and category name)

        Args:
            form (str): The form name (without the "Form:" prefix)

        Returns:
            List[str]: The page names
        """
        return self._get_list_of_instances(form)
    
    def get_playbook_wiki(self, page_name, page_form=None):
        """Return a playbook object including content

        Args:
            page_name (str): The playbook page name

        Returns:
            dict: The playbook object
        """
        playbook = dict()
        playbook["name"] = page_name
        playbook["page_name"] = page_name
        playbook["url"] = self.kb.wiki_url_pattern.format(page_name=page_name)
        playbook["form"] = self.get_form_ask(page_name) if page_form is None else page_form

        playbook["content"] = self.get_page(page_name, playbook["form"])
        for name in self.kb.name_fields:
            if name in playbook["content"]:
                playbook["name"] = playbook["content"][name][0]
                break
        
        playbook["objects"] = self._get_instance_objects_all(page_name, new_mode=True)
        
        return playbook

    def get_page_content(self,page_name,raw=False, return_text=False):
        """Return the content of a playbook or playbook object
        
        Args:
            page_name (str): The playbook or playbook object page name
            raw (bool): If true, return the content in pseudo rdf (predicate,object), 
            else return the content as a dictionary, with values as lists
            return_text (bool): If true, additionally returns the content of the page as text
        """
        if self.get_page_exists(page_name) is False:
            return None

        content_raw = self._get_instance_info_wide(page_name)
        text_raw = None
        if return_text:
            text_raw = self.site.pages[page_name].text()
        if raw:
            if return_text:
                return content_raw, text_raw
            else:
                return content_raw
        content_dict = {}
        for k, v in content_raw:
            content_dict[k] = content_dict.get(k, []) + [v]
        
        # {property: ["value_1", "value_2", "..."]}
        if return_text:
            return content_dict, text_raw
        else:
            return content_dict
    
    def get_page_exists(self, page_name):
        """Return whether the page exists"""
        return self.site.pages[page_name].exists
    
    def get_all_forms(self):
        """Return a list of all forms

        Returns:
            List[str]: List of all page names that have a form associated with them, to access the form add the prefix "Form:"
        """
        return self._get_all_namespace_instances("Form")
    
    def get_all_templates(self):
        """Return a list of all templates

        Returns:
            List[str]: List of all page names that have a template associated with them, to access the template add the prefix "Template:"
        """
        return self._get_all_namespace_instances("Template")
    
    def get_all_properties(self):
        """Return a list of all properties

        Returns:
            List[str]: List of all page names that have a property associated with them, to access the property add the prefix "Property:"
        """
        return self._get_all_namespace_instances("Property")
    
    def get_form_variables(self,form_name, source=None):
        """Return a form's variables in dictionary format"""
        return {key:value for key,value in self._get_form_variables(form_name, source=source)}
    
    def get_page_categories(self,page_name):
        """Return a page's categories in list format"""
        return self._get_page_categories(page_name)
    
    def get_form(self,form_name, source=None):
        """Return a form in dictionary format or None if the form does not exist
        The form is a dictionary with the following structure:
        {
            "source" : "source text",
            "variables" : {get_form_variables(form_name)}
        }

        Args:
            form_name (str): The form name (without the prefix "Form:")
            source (str, optional): The source code of the form. Basically converts the source code to a dictionary. Defaults to None.
            
        Returns:
            dict: The form object
        """
        if source is None:
            source = self._get_page_text("Form:"+form_name)
        if source is None:
            return None
        form_variables = self.get_form_variables(form_name, source=source)
        return {
            "source" : source,
            "variables" : form_variables
        }
    
    def get_template(self,template_name, source=None):
        """Return a template in dictionary format
        The template is a dictionary with the following structure:
        {
            "source" : "source text",
            "info" : {get_template_info(template_name)}
        }
        
        Args:
            template_name (str): The template name
            source (str, optional): The source code of the template. Basically converts the source code to a dictionary. Defaults to None.

        Returns:
            dict: The template object
        """
        template_info = self._get_template_info(template_name,include_source=True, source=source)
        if not template_info:
            return None
        template_info, source = template_info
        return {
            "source" : source,
            "info" : template_info
        }
        
    def get_template_info(self,template_name, source=None):
        """Return template variables in dictionary format"""
        # {
        #     "field_name" : {
        #         "label" : "display label",
        #         "property" : "semantic property name",
        #         "list" : "seperator" # if the field is a list, seperator is the seperator between the list items, otherwise the field is absent
        #     },
        #     ...
        # }
        return self._get_template_info(template_name, source=source)
    
    def get_property(self,property_name, source=None):
        """Return a property in dictionary format"""

        if source is None:
            source = self._get_page_text(f"Property:{wiki_name(property_name)}")
        if source is None:
            return dict()
        semantic_dict = dict()
        mediawiki_dict = dict()
        
        # Find all [[...]]
        re_search = re.findall(r"\[\[(.*?)\]\]",source)
        for match in re_search:
            # Semantic properties have a :: seperator, mediawiki properties have a single :
            # Check which comes first
            if "::" in match and match.find("::") <= match.find(":"): # Semantic property
                # Split on the first ::
                key, value = match.split("::",1)
                # Remove the leading and trailing whitespace
                key, value = key.strip(), value.strip()
                # Add to the semantic dictionary
                semantic_dict[key] = semantic_dict.get(key, []) + [value]
            elif ":" in match: # Mediawiki property
                # Split on the first :
                key, value = match.split(":",1)
                # Remove the leading and trailing whitespace
                key, value = key.strip(), value.strip()
                # Add to the mediawiki dictionary
                mediawiki_dict[key] = mediawiki_dict.get(key, []) + [value]
            else: # Unexpected match format, print for debugging
                self.logger.warning(f"Unexpected match format: {match}, in {property_name}")
            
        return {
            "semantic" : semantic_dict,
            "mediawiki" : mediawiki_dict,
            "source" : source
        }
    
    def get_category(self,category_name, source=None):
        """Return a category source code or None if the category does not exist

        Args:
            category_name (str): The category name (without the prefix "Category:")
            source (str, optional): The source code of the category. Defaults to None.

        Returns:
            dict|None: The category contents in dictionary format or None if the category does not exist
        """

        if source is None:
            source = self._get_page_text(f"Category:{wiki_name(category_name)}")
        if source is None:
            return None
        return {
            "source" : source
        }

    
    def create_page(self,name,form,content):
        """Create a new playbook or playbook object"""
        self._create_form_import(form, name,[])
        self.update_page(page_name=name,form=form, add_content=content)
    
    def create_category(self,category_name, source, comment=None):
        """Create a new category or overwrite an existing category with the given source code"""
        if comment is None:
            self._edit_from_source(f"Category:{wiki_name(category_name)}", source)
        else:
            self._edit_from_source(f"Category:{wiki_name(category_name)}", source, comment)
    
    def create_property(self,property_name, source, comment=None):
        """Create a new property or overwrite an existing property with the given source code"""
        if comment is None:
            self._edit_from_source(f"Property:{wiki_name(property_name)}", source)
        else:
            self._edit_from_source(f"Property:{wiki_name(property_name)}", source, comment)
        
    def create_template(self,template_name, source, comment=None):
        """Create a new template or overwrite an existing template with the given source code"""
        if comment is None:
            self._edit_from_source(f"Template:{wiki_name(template_name)}", source)
        else:
            self._edit_from_source(f"Template:{wiki_name(template_name)}", source, comment)
    
    def create_form(self,form_name, source, comment=None):
        """Create a new form or overwrite an existing form with the given source code"""
        if comment is None:
            self._edit_from_source(f"Form:{wiki_name(form_name)}", source)
        else:
            self._edit_from_source(f"Form:{wiki_name(form_name)}", source, comment)
    
    def delete_page(self,page_name):
        """Delete a playbook or playbook object"""
        if self.connected:
            self._delete_wiki_object(page_name)
    
    def rename_page(self,page_name,new_name):
        """Rename a playbook or playbook object"""
        if page_name == new_name:
            self.logger.warning("Rename called with same name Page:%s",page_name)
            return False
        if self.site.pages[new_name].exists:
            self.logger.warning("Rename called with existing name Page:%s NewName:%s",page_name,new_name)
            return False
        if not self.site.pages[page_name].exists:
            self.logger.warning("Rename called with non-existing name Page:%s NewName:%s",page_name,new_name)
            return False
        try:
            self.site.pages[page_name].move(new_name,"Renamed by playbook app")
            return True
        except Exception as e:
            self.logger.warning("Rename failed Page:%s NewName:%s Error:%s",page_name,new_name,e)
            return False
    
    def update_page(self,page_name,form,add_content=dict(),remove_content=dict(),reset_page=False):
        """Update the specified instance with new information.

        Args:
            name (str): Name of the instance to update
            form (str): Name of the form that is used for the type of the object
            add_content (Dict{str:List[str,str,...]}): Predicate and object additions 
            to be made to the instance
            remove_content (Dict{str:List[str,str,...]}): Predicate and object removals
            to be made to the instance
            reset_page (bool): If true, the page will be reset to the form template and
            only the content specified in add_content will be added
        """
        if not add_content and not remove_content:
            self.logger.warning("Update called with no changes Page:%s Form:%s",page_name,form)
            return
        if reset_page:
            content = set()
        else:
            content = set(self.get_page_content(page_name,raw=True))

        for k,v in add_content.items():
            if k == 'case_table':
                continue

            for value in v:
                item = (k,value.strip())
                content.add(item)
        for k,v in remove_content.items():
            for value in v:
                item = (k,value.strip())
                content.discard(item)
        
        if add_content and 'case_table' in add_content:
            self._create_form_import(form, page_name,list(content), reset_page=True)
            table_markup = ['','{| class="wikitable" style="margin:auto"','|-']
            table_markup += ['! Case !! Step']
            for case,switch_steps in add_content['case_table'].items():
                for step in switch_steps:
                    table_markup.append('|-')
                    table_markup.append('| {} || {}'.format(case,step))
            table_markup.append('|}')
            self.site.pages[page_name].append('\n'.join(table_markup),summary='Switch condition table')            
        else:
            self._create_form_import(form, page_name,list(content), reset_page=True)
        self._update_playbook(page_name,form,list(content))
    
    def set_page(self,page_name,context={},template_name='wiki_page.jinja',dry_run=False):
        """Set the content of a playbook or playbook object
        
        Args:
            page_name (str): The playbook or playbook object page name
        
        Returns:
            int: 0 if everything went well, an error code otherwise
            
        Error Codes:
            1: General error
            2: Error rendering template
            3: Error setting page
            # More as needed
        """
        try:
            template = self.jinja.get_template(template_name)
            template_str = template.render(context)
        except Exception as e:
            self.logger.error("Error rendering template %s",template_name)
            self.logger.error(e)
            return 2
        try:
            if dry_run:
                path = Path(__file__).parent / 'wikitext'
                path.mkdir(parents=True,exist_ok=True)
                with open(path / (re.sub('[^A-Za-z0-9]','_',page_name)+".txt"),"w") as f:
                    f.write(template_str)
                pass
            else:
                if self.connected:
                    self.site.pages[page_name].edit(template_str, 'Wiki page updated')
        except Exception as e:
            self.logger.error("Error setting page %s",page_name)
            self.logger.error(e)
            return 3
        return 0
    
    def set_bpmn(self,page_name,bpmn_xml):
        if self.connected:
            self.site.pages[f'BPMN:{page_name}'].edit(bpmn_xml, 'Updated BPMN!')
    
    def get_form_ask(self,page_name):
        """Return the form of a page using ask query (faster?)"""
        page_name = page_name.replace('_',' ')
        query = (
            f"[[{page_name}]]" + 
            '|?Category'
        )
        response = self.site.api('ask', query=query)
        if len(response['query']['results']) == 0:
            raise ValueError(f"Page {page_name} does not exist")
        try:
            form_name = response['query']['results'][page_name]['printouts']['Category'][0]['fulltext']
            return form_name.replace('Category:','')
        except Exception as e:
            self.logger.error("Error getting form for page %s",page_name)
            self.logger.error("Response: %s",response)
            raise e
    
    def get_page(self,page_name, form_name=None):
        """Returns formdata for a page"""
        if form_name is None:
            form_name = self.get_form_ask(page_name)
        form = sasp.models.Form.objects.get(name=form_name)
        form = {
            field['key'] : field for field in form.fields
        }
        page_name = page_name.replace('_',' ')
        query = (
            f"[[{page_name}]]" + 
            '|' +
            "|".join([f"?{field}" for field in form])
        )
        response = self.site.api('ask', query=query)
        try:
            content = dict()
            for property,values in response['query']['results'][page_name]['printouts'].items():
                if len(values) == 0:
                    continue
                elif isinstance(values[0],dict):
                    content[property] = [value['fulltext'] for value in values]
                else:
                    content[property] = [str(value) for value in values]
                if form[property]['value-type'] == 'boolean':
                    content[property] = ['Yes' if val else 'No' for val in content[property]] if values else ['No']
            return content
        except Exception as e:
            self.logger.error("Error getting page %s",page_name)
            self.logger.error("Response: %s",response)
            raise e

    def get_last_change(self,page_name):
        """Return the timestamp of the last change to the page"""        
        pb_wiki_page = self.site.pages[page_name]
        if not pb_wiki_page.exists:
            self.logger.error("Page %s does not exist",page_name)
            return None
        revisions = [revision for revision in pb_wiki_page.revisions(limit=1)]
        if len(revisions) == 0:
            return 0
        last_change_wiki = mktime(revisions[0]['timestamp'])
        last_change_wiki += self.kb.wiki_time_offset*60*60
        return last_change_wiki
    
    def search(self,query,regex=False):
        """Search for pages that match the query"""
        results = set()

        if regex:
            playbooks = (
                sasp.models.Playbook.objects.filter(name__regex=query) |
                sasp.models.Playbook.objects.filter(wiki_page_name__regex=query)
            )
            for pb in playbooks:
                results.add(pb.wiki_page_name)
            del playbooks

            playbook_objects = (
                sasp.models.Playbook_Object.objects.filter(name__regex=query) |
                sasp.models.Playbook_Object.objects.filter(wiki_page_name__regex=query)
            )
            for pb in playbook_objects:
                results.add(pb.wiki_page_name)
            del playbook_objects
        else:
            playbooks = (
                sasp.models.Playbook.objects.filter(name__icontains=query) |
                sasp.models.Playbook.objects.filter(wiki_page_name__icontains=query)
            )
            for pb in playbooks:
                results.add(pb.wiki_page_name)
            del playbooks

            playbook_objects = (
                sasp.models.Playbook_Object.objects.filter(name__icontains=query) |
                sasp.models.Playbook_Object.objects.filter(wiki_page_name__icontains=query)
            )
            for pb in playbook_objects:
                results.add(pb.wiki_page_name)
            del playbook_objects
        
        return results

    def semantic_search(self, subject=None, predicate=None, object=None, regex=False, playbook_pk=None):
        """
        Case insensitive or regex search semantic relations for the specified subject, predicate, and/or object and return the set of all subjects that match the query.

        Args:
            subject (str, optional): The string to filter the subject field by. Defaults to None, which will not filter by subject.
            predicate (str, optional): The string to filter the predicate field by. Defaults to None, which will not filter by predicate.
            object (str, optional): The string to filter the object field by. Defaults to None, which will not filter by object.
            regex (bool, optional): Whether to use regex or case insensitive search. Defaults to False, which will use case insensitive search.
            playbook_pk (int|str|Playbook, optional): The primary key or name of the playbook to filter by. Improves performance. Defaults to None, which will not filter by playbook.


        Returns:
            list[tuple[str, str, str]]: A list of tuples containing the subject, predicate, and object of each semantic relation that matches the query.
        """
        results = []

        if playbook_pk is None:
            playbook = None
        elif isinstance(playbook_pk, sasp.models.Playbook):
            playbook = playbook_pk
        elif isinstance(playbook_pk, int):
            try:
                playbook = sasp.models.Playbook.objects.get(pk=playbook_pk)
            except sasp.models.Playbook.DoesNotExist:
                playbook = None
        elif isinstance(playbook_pk, str):
            try:
                playbook = sasp.models.Playbook.objects.get(wiki_page_name=playbook_pk)
            except sasp.models.Playbook.DoesNotExist:
                playbook = None

        if playbook:
            semantic = sasp.models.Semantic_Relation.objects.filter(playbook=playbook)
        else:
            semantic = sasp.models.Semantic_Relation.objects.all()
        if regex:
            if subject:
                semantic = semantic.filter(subject__regex=subject)
            if predicate:
                semantic = semantic.filter(predicate__regex=predicate)
            if object:
                semantic = semantic.filter(object__regex=object)
            for rel in semantic:
                results.append((rel.subject, rel.predicate, rel.object))
        else:
            if subject:
                semantic = semantic.filter(subject__icontains=subject)
            if predicate:
                semantic = semantic.filter(predicate__icontains=predicate)
            if object:
                semantic = semantic.filter(object__icontains=object)
            for rel in semantic:
                results.append((rel.subject, rel.predicate, rel.object, rel.playbook))
        
        return results
    
    def get_playbook_db(self,playbook: str):
        """Return the playbook object for the specified playbook

        Args:
            playbook (str): The playbook page name

        Returns:
            Playbook: The playbook object
        """
        try:
            return sasp.models.Playbook.objects.get(wiki_page_name=playbook)
        except sasp.models.Playbook.DoesNotExist:
            self.logger.error("Playbook %s does not exist",playbook)
            return None
    
    def get_playbook_url(self, playbook) -> str:
        """Return the url for the specified playbook

        Args:
            playbook (str|Playbook): The playbook page name or playbook object
        
        Returns:
            str: The url for the playbook
        """
        if isinstance(playbook, sasp.models.Playbook):
            return playbook.get_absolute_url()
        else:
            return self.get_playbook_db(playbook).get_absolute_url()
    
    def get_playbook_object(self,playbook_object: str):
        """Return the playbook object for the specified playbook object

        Args:
            playbook_object (str): The playbook object page name

        Returns:
            Playbook_Object: The playbook object
        """
        try:
            return sasp.models.Playbook_Object.objects.get(wiki_page_name=playbook_object)
        except sasp.models.Playbook_Object.DoesNotExist:
            self.logger.error("Playbook object %s does not exist",playbook_object)
            return None

    def get_playbook_object_url(self, playbook_object) -> str:
        """Return the url for the specified playbook object

        Args:
            playbook_object (str|Playbook_Object): The playbook object page name or playbook object
        
        Returns:
            str: The url for the playbook object
        """
        if isinstance(playbook_object, sasp.models.Playbook_Object):
            return playbook_object.get_absolute_url()
        else:
            return self.get_playbook_object(playbook_object).get_absolute_url()