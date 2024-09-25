from .models import Playbook, Playbook_Object, Semantic_Relation
from .wiki_interface import Wiki
from .knowledge import KnowledgeBase
import json,logging,re

class WikiDBSync:
    logger = logging.getLogger(__name__)
    def __init__(self):
        self.kb = KnowledgeBase()
        self.wiki = None

    def __new__(cls, *args, **kwargs):
        """Override __new__ to make this a singleton class"""
        if not hasattr(cls, 'instance'):
            cls.instance = super(WikiDBSync, cls).__new__(cls)
        return cls.instance
    
    def update_playbooks(self):
        """Get playbooks from wiki and update database.
        Only updates basic information, not content or objects, use update_playbook for that"""
        if self.wiki is None:
            self.wiki = Wiki()
        # {page_name :
        #         {
        #             "name" : str,
        #             "page_name" : str,
        #             "url" : str,
        #             "form" : str,
        #         }}

        wiki_playbooks = self.wiki.get_playbooks_ask()
        db_playbooks = Playbook.objects.all()
        for db_playbook in db_playbooks:
            if db_playbook.wiki_page_name not in wiki_playbooks:
                db_playbook.delete(delete_wiki_page=False)
            else:
                wiki_playbooks.pop(db_playbook.wiki_page_name)
        for page,playbook_dict in wiki_playbooks.items():
            pb = Playbook(wiki_page_name=page, name=playbook_dict['name'])
            pb.wiki_form = playbook_dict['form']
            # Content is empty, so we suppress the update of the wiki page the save method would normally do
            pb.save(from_wiki=True)
        
        return True
    
    def update_playbook(self,playbook, force=False):
        """Get playbook objects from wiki and update database"""
        if self.wiki is None:
            self.wiki = Wiki()

        if isinstance(playbook,Playbook):
            playbook_db = playbook
            playbook_page = playbook_db.wiki_page_name
        else:
            playbook_page = playbook
            # If playbook does not exist in database, sync and try again. If it still does not exist, raise error
            try:
                playbook_db = Playbook.objects.get(wiki_page_name=playbook_page)
            except Playbook.DoesNotExist:
                self.update_playbooks()
                playbook_db = Playbook.objects.get(wiki_page_name=playbook_page)
        
        # Check last update time and only update if needed
        if not force:
            last_change_wiki = self.wiki.get_last_change(playbook_page)
            last_change_db = playbook_db.last_change.timestamp()
        else:
            last_change_wiki = 1
            last_change_db = 0
        
        if last_change_wiki > last_change_db or not playbook_db.content:
            self.logger.info("Updating playbook %s",playbook_page)
        else:
            self.logger.info("Playbook %s is up to date",playbook_page)
            return False

        playbook_wiki = self.wiki.get_playbook_wiki(playbook_page,playbook_db.wiki_form)
        wiki_objects = set(playbook_wiki['objects'])

        # Sync playbook itself
        playbook_db.name = playbook_wiki['name']
        if 'description' in playbook_wiki:
            playbook_db.description = playbook_wiki['description']
        playbook_db.content = self.wiki.get_page(playbook_page,playbook_db.wiki_form)
        playbook_db.save(from_wiki=True)
        
        db_objects = Playbook_Object.objects.filter(playbook=playbook_db)

        # Objects already in db
        for db_object in db_objects:
            if db_object.wiki_page_name not in wiki_objects: # Object no longer in wiki
                db_object.delete()
            else:
                wiki_objects.remove(db_object.wiki_page_name) # Object already in db
        

        # Objects not yet in db
        for wiki_object in wiki_objects:
            pb_o = Playbook_Object(playbook=playbook_db)
            pb_o.wiki_page_name=wiki_object

            pb_o.wiki_form = playbook_wiki['objects'][wiki_object]['form_name']
            self.update_playbook_object(pb_o)
        
        return True
    
    def update_playbook_object(self,pb_o):
        """Get playbook object content from wiki and update database"""
        if self.wiki is None:
            self.wiki = Wiki()

        if isinstance(pb_o,Playbook_Object):
            pb_o_db = pb_o
            pb_o_page = pb_o_db.wiki_page_name
        else:
            pb_o_page = pb_o
            pb_o_db = Playbook_Object.objects.get(wiki_page_name=pb_o_page)

        # Check last update time and only update if needed
        last_change_wiki = self.wiki.get_last_change(pb_o_page)
        if pb_o_db.last_change is None:
            last_change_db = 0
        else:
            last_change_db = pb_o_db.last_change.timestamp()
        if last_change_wiki > last_change_db + 5: # Add 5 seconds because if you just created the object, the wiki page will be updated after the object is created
            self.logger.info("Updating playbook object %s",pb_o_page)
        else:
            self.logger.info("Playbook object %s is up to date",pb_o_page)
            return False
        
        if pb_o_db.wiki_form == "Switch Condition Step":
            pb_o_wiki, pb_o_wiki_text = self.wiki.get_page_content(pb_o_page,return_text=True)
            # Try to get the case dictionary from the mediawiki table
            try:
                #  Find table enclosed in {| and |}
                table = re.search(r"\{\|.*\|\}",pb_o_wiki_text,re.DOTALL).group(0)
                if "class=\"wikitable\"" in table: # Check if table is a mediawiki table as redundant check
                    table = table.split("\n")
                    table = [line[1:] for line in table if "||" in line] # Remove first character of each line ("|") and only keep lines with "||" meaning they are a table row
                    table = {key.strip():value.strip() for key,value in [line.split("||") for line in table]}
                    table = {key:[val.strip() for val in value.split(",")] for key,value in table.items()}
                else:
                    table = dict()
            except Exception as e:
                self.logger.warning("Could not parse case table for %s: %s",pb_o_page,e)
                table = dict()
            pb_o_wiki["case_table"] = table
        else:
            pb_o_wiki = self.wiki.get_page(pb_o_db.wiki_page_name,pb_o_db.wiki_form)
        
        pb_o_db.content = pb_o_wiki

        pb_o_db.name = pb_o_page
        for name in self.kb.name_fields:
            if name in pb_o_wiki:
                pb_o_db.name = pb_o_wiki[name][0]
                break
        pb_o_db.save(from_wiki=True)

        return True

        # Edge case: Object was registered as belonging to playbook A, inbetween syncs the page on the
        # wiki was deleted and recreated as belonging to playbook B. This will not be detected by the
        # syncs, so we need to check for this somehow.

    def update_playbook_object_relations(self,pb_o):
        """Update relations of a playbook object"""
        if self.wiki is None:
            self.wiki = Wiki()

        if isinstance(pb_o,Playbook_Object):
            pb_o_db = pb_o
            pb_o_page = pb_o_db.wiki_page_name
        else:
            pb_o_page = pb_o
            pb_o_db = Playbook_Object.objects.get(wiki_page_name=pb_o_page)

        self.logger.info("Updating playbook object relations for %s",pb_o_page)

        # Get relations from wiki
        pb_o_wiki = self.wiki.get_page_content(pb_o_page)
        if not pb_o_wiki:
            pb_o_wiki = dict()

        # Clear existing relations with this playbook object as subject
        Semantic_Relation.objects.filter(playbook=pb_o_db.playbook,subject=pb_o_db.wiki_page_name).delete()

        # Add new relations
        relations = []
        for key in pb_o_wiki:
            for value in pb_o_wiki[key]:
                relations.append(Semantic_Relation(playbook=pb_o_db.playbook,subject=pb_o_db.wiki_page_name,predicate=key,object=value))
        if relations:
            Semantic_Relation.objects.bulk_create(relations)

        return True


