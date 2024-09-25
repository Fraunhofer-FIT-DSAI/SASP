import logging

from threading import Thread


from .db_syncs import WikiDBSync
from .knowledge import KnowledgeBase
from .models import (Automation_Instance, Playbook,
                     Playbook_Object)
from .utils import wiki_name
from .wiki_forms import WikiFormManager


class LogicManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(LogicManager, cls).__new__(cls)
        return cls.instance
        
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kb = KnowledgeBase()
        self.wiki = None
        self.db_sync = WikiDBSync()
    
    def templateFromObject(self, object, target, use_mkey=False):
        """Creates a template from a playbook or playbook object

        Args:
            object (Playbook|Playbook_Object): The object to create a template from
            target (Playbook|None): The playbook to create the template for, or None if it is a new playbook
            
        Returns:
            dict: The template
        """
        if isinstance(object, Playbook):
            # Load equivalent Playbook_Object
            object = Playbook_Object.objects.get(wiki_page_name=object.wiki_page_name)
        elif not isinstance(object, Playbook_Object):
            self.logger.error("Object is not a playbook or playbook object")
            return None
        if object.wiki_form == 'root':
            wiki_form = Playbook.objects.get(wiki_page_name=object.wiki_page_name).wiki_form
        else:
            wiki_form = object.wiki_form
        form = WikiFormManager().get_form(wiki_form)
        form = {
            x.get('semantic_property', x['key']): x
            for x in form['fields']
        }
        content = object.content
        for key in list(content.keys()):
            if key not in form:
                del content[key]
        if any(form[key]["value-type"] == 'object' for key in content):
            if target is None:
                # Discard all foreign key objects
                pb_objects = set()
            elif isinstance(target, Playbook):
                # Load objects from target playbook
                pb_objects = Playbook_Object.objects.filter(playbook=target)
            elif isinstance(target, Playbook_Object):
                # Load objects from target playbook
                pb_objects = Playbook_Object.objects.filter(playbook=target.playbook)
            else:
                self.logger.error("Target is not a playbook or playbook object or None")
                return None
            # We only need the wiki page names
            pb_objects = {wiki_name(x.wiki_page_name) for x in pb_objects}
        else:
            pb_objects = None

        template = {}
        for key in content:
            form_prop = form[key]
            value = content[key]
            # "text", # A single line of text (e.g. name, email, phone number)
            # "textarea", # A multi-line text area (e.g. address, description)
            # "list", # A list of values with no minimum or maximum length
            # "choose-one", # A list of values from which the user must choose exactly one (e.g. a dropdown menu)
            # "choose-many", # A list of values from which the user must choose at least one (e.g. a list of checkboxes)
            # "checkbox", # A boolean value
            # "date", # A date value
            if not value:
                continue
            if form_prop['value-type'] == 'object':
                # Only include objects that are in the playbook
                value = [x for x in value if wiki_name(x) in pb_objects]
                if not value:
                    continue
            if form_prop["field-type"]=="text" or form_prop["field-type"]=="textarea":
                template[key] = value[0]
            elif form_prop["field-type"]=="list":
                template[key] = ", ".join(value)
            elif form_prop["field-type"]=="choose-one":
                # assert isinstance(value, list) and len(value)==1, f"Invalid value for {key}: {value}"
                template[key] = value[0]
            elif form_prop["field-type"]=="choose-many":
                template[key] = value
            elif form_prop["field-type"]=="checkbox":
                template[key] = True if value[0]=="Yes" else False
            else:
                template[key] = ", ".join(value)
        if use_mkey:
            template = {
                form[key]["machine-key"]: template[key]
                for key in template if "machine-key" in form[key]
            }
        return template
    
class ThreadManager:
    """Keeps track of thread instances connected to automation instances.
    """

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ThreadManager, cls).__new__(cls) 
        return cls.instance
    
    def __init__(self):
        self.threads = {}
        self.logger = logging.getLogger(__name__)
    
    def spawn_thread(self, playbook, case_id):
        """Spawns a new thread and returns the id of the thread.
        """
        from .external_apis.hive_cortex_api import HiveAPI
        from .automation_component.hive_playbook_instances import Workflow_Instance
        # Start high to avoid collisions with the ids of threads that have already finished
        new_id = max(self.threads.keys(), default=0) + 1

        # wrap around to stay within the range of a 32 bit integer
        if new_id > 2147483647:
            if len(self.threads) == 2147483647:
                raise Exception("Too many threads. Like way too many, how did you even get here?")
            new_id = 0
            while new_id in self.threads:
                new_id += 1
        
        db_object = Automation_Instance(
            playbook=playbook, 
            case_id=case_id, 
            case_name=HiveAPI().get_case_fields(case_id, pythonify=True).get("title", "Untitled Case"),
            thread_id=new_id
        )        
        db_object.initialize()

        def setup_workflow():
            workflow = Workflow_Instance(playbook.id, root_workflow=True, name=playbook.name, case_id=case_id, db_object=db_object)
            workflow.start()
            
        if False: #DEBUG: Run in main thread for debugging
            setup_workflow()
            thread = None
        else:
            thread = Thread(target=setup_workflow, daemon=True)
            thread.start()
        
        self.threads[new_id] = (db_object, thread)
        return new_id
    
    def get_thread(self, thread_id):
        """Returns the database object and thread instance of the given thread id.

        Args:
            thread_id (int): The id of the thread.

        Returns:
            tuple: (db_object, thread)
        """
        if thread_id not in self.threads:
            self.logger.error(f"Thread {thread_id} not found")
            self.logger.info(f"Threads: {self.threads}")
            return None
        return self.threads[thread_id]
    
    def kill_thread(self, thread_id, **kwargs):
        # Can be achieved through events or custom exceptions, but is out of scope for now
        # The threads only interact with their own resources and the database, so they should be safe to just leave running
        if thread_id not in self.threads:
            self.logger.warning(f"kill_thread called on thread {thread_id}, but the thread does not exist.")
        elif self.threads[thread_id][1].is_alive():
            if kwargs.get("ignore_implementation_warning", False):
                pass
            else:
                self.logger.warning(f"Method kill_thread not implemented. Thread {thread_id} will continue running.")
        else:
            self.logger.info(f"kill_thread called on thread {thread_id}, but the thread is not running.")
        pass

    def register_deletion(self, thread_id, db_object, force=False):
        """Registers the deletion of an automation instance with the thread manager. And watches for conflicts.

        Args:
            thread_id (int): The id of the thread.
            db_object (Automation_Instance): The database object of the automation instance.
            force (bool, optional): If True, the deletion will be forced, even if there are conflicts. Defaults to False.

        Returns:
            bool: True if the deletion was successful, with no conflicts. False otherwise.
            list, None: A list of conflicts, or None if there were no conflicts.
        """
        success = True
        conflicts = []
        
        if thread_id not in self.threads:
            self.logger.error(f"Thread {thread_id} not found")
            success = False
            conflicts.append(
                {
                    "conflict" : "Thread not found",
                    "conflict_code" : 1,
                }
            )
        else: # Cases that depend on the object being present
            if self.threads[thread_id][0] != db_object:
                self.logger.error(f"Database object {db_object} does not match database object {self.threads[thread_id][0]} of the thread")
                success = False
                conflicts.append(
                    {
                        "conflict" : "Database object mismatch",
                        "conflict_code" : 2,
                        "db_object_argument" : db_object,
                        "db_object_database" : self.threads[thread_id][0],
                    }
                )
            if self.threads[thread_id][1].is_alive():
                self.logger.warning(f"Thread {thread_id} is still running and will not be deleted")
                success = False
                conflicts.append(
                    {
                        "conflict" : "Thread still running",
                        "conflict_code" : 3,
                    }
                )
                
        if db_object.thread_id != thread_id:
            self.logger.error(f"Thread id {thread_id} does not match thread id {db_object.thread_id} of the database object")
            success = False
            conflicts.append(
                {
                    "conflict" : "Thread id mismatch",
                    "conflict_code" : 4,
                    "thread_id_argument" : thread_id,
                    "thread_id_database" : db_object.thread_id,
                }
            )
        
        if success or force:
            if thread_id in self.threads:
                del self.threads[thread_id]
        
        if success:
            return True, None
        else:
            return False, conflicts