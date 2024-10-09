import logging
import configparser
import urllib.parse
from pathlib import Path
from dotenv import dotenv_values
from .utils import wiki_name
from .localization.english import HelpTexts, Messages, Labels
from sasp.pytools import classproperty
# Pages in these categories define playbooks:
PLAYBOOK_CATEGORIES = {"Playbook","CACAO Playbook"}

# These forms define the common properties for their respective types
ABSTRACT_FORMS = {
    'Target',
    'Data Marking',
    'Workflow Step'
}

# Text fields in which special characters like commas are allowed
FREE_TEXT_FIELDS = {
    'name',
    'description',
    'command',
    'commandb64'
}

class Sharing:
    @classproperty
    def supported(cls):
        import sasp.models.cacao_1_1 as cacao_1_1
        return {
            "JSON": {
                "Import": [
                    (cacao_1_1.CACAO_1_1.cls_label, 'sharing-import-json-cacao-1-1')
                ],
                "Export": [
                    (cacao_1_1.CACAO_1_1.cls_label, 'sharing-export-json-cacao-1-1')
                ]
            },
            "MISP": {
                "Import": [
                    (cacao_1_1.CACAO_1_1.cls_label, 'sharing-import-misp-cacao-1-1')
                ],
                "Export": [
                    (cacao_1_1.CACAO_1_1.cls_label, 'sharing-export-misp-cacao-1-1')
                ]
            },
            "Kafka": {
                "Import": [
                    (cacao_1_1.CACAO_1_1.cls_label, 'sharing-import-kafka-cacao-1-1')                    
                ],
                "Export": [
                    (cacao_1_1.CACAO_1_1.cls_label, 'sharing-export-kafka-cacao-1-1')
                ]
            }
        }

class KnowledgeBase:
    logger = logging.getLogger(__name__)

    help_texts = HelpTexts
    messages = Messages
    labels = Labels

    wiki_time_offset = 2
    
    
    regex_wiki_name = r"^[A-Z][A-Za-z0-9 -]+$"
    regex_wiki_name_allowed = r"[A-Za-z0-9 -]"
    regex_wiki_name_disallowed = r"[^A-Za-z0-9 -]"

    # Should point to capturing-tool
    project_folder = Path(__file__).parent / '..'
    # Points to the .env file containing the wiki configuration
    config_path = project_folder / 'config' / 'config.ini'
    config_keys_path = project_folder / 'config' / 'keys.ini'
    
    config = configparser.ConfigParser()
    config.read(config_path)
    config_keys = configparser.ConfigParser()
    config_keys.read(config_keys_path)
    
    host = urllib.parse.urlparse(config.get('Wiki', 'url')).netloc
    wiki_url_pattern = config.get('Wiki', 'url') + config.get('Wiki', 'user_path') + '{page_name}'
    wiki_api_url = config.get('Wiki', 'url') + config.get('Wiki', 'api_path')

    hive_url = None
    hive_api_key = None

    cortex_url = None
    cortex_api_key = None

    misp_url = config.get('MISP', 'url', fallback='')
    misp_key = config_keys.get('MISP', 'key', fallback='')
    misp_cert = config_keys.get('MISP', 'cert', fallback='')
    
    name_fields = {
        'name',
        'Name',
        'hasName',
        'HasName',
    }
    form_properties = dict()

    # Supported playbook formats and base forms
    base_forms = {
        "SAPPAN" : "Playbook",
        "CACAO" : "CACAO_Playbook",
    }

    # Known forms that describe a playbook
    form_properties["playbook"] = {
        "CACAO_Playbook", 
        "CACAO Playbook",
        "Playbook",
    }
    # Known forms that describe a playbook step
    form_properties["steps"] = {
        "Final_Step",
        "Initial_Step",
        "Intermediate_Step",
        "Optional_Step",
        "Exclusive_Choice_Step",
        "While_Condition_Step",
        "Switch_Condition_Step",
        "Start_Step",
        "Single_Action_Step",
        "Playbook_Step",
        "Parallel_Step",
        "If_Condition_Step",
        "End_Step",
    }
    # Known forms that are associated with a cacao playbook
    form_properties["CACAO"] = {
        "GPS_Location",
        "Group_Target",
        "HTTP_API_Target",
        "IEP_Marking",
        "If_Condition_Step",
        "Individual_Target",
        "Kali_Linux_Target",
        "Location_Target",
        "Organization_Target",
        "Parallel_Step",
        "Playbook_Step",
        "Sector_Target",
        "Security_Infrastructure_Category_Target",
        "Signature",
        "Single_Action_Step",
        "SSH_CLI_Target",
        "Start_Step",
        "Statement_Marking",
        "Switch_Condition_Step",
        "Target",
        "TLP_Marking",
        "Variable",
        "While_Condition_Step",
        "Workflow_Step",
        "Attack_Agent_Target",
        "Attack_Group_Target",
        "Attacker_Target",
        "CACAO_Playbook",
        "Civic_Location",
        "Command",
        "Contact_Information",
        "Data_Marking",
        "End_Step",
        "Extension",
        "External_Reference",
        "General_Network_Address_Target",
    }
    # Known forms associated with sappan playbooks
    form_properties["SAPPAN"] = {
        "Intermediate_Step",
        "Optional_Step",
        "Playbook",
        "Tool",
        "Action",
        "Exclusive_Choice_Step",
        "Final_Step",
        "Initial_Step",
    }
    form_properties["targets"] = {
        "Group_Target",
        "HTTP_API_Target",
        "Individual_Target",
        "Kali_Linux_Target",
        "Location_Target",
        "Organization_Target",
        "Sector_Target",
        "Security_Infrastructure_Category_Target",
        "SSH_CLI_Target",
        "Target",
        "Attack_Agent_Target",
        "Attack_Group_Target",
        "Attacker_Target",
        "General_Network_Address_Target",
    }
    form_properties["data_markings"] = {
        "Statement_Marking",
        "TLP_Marking",
        "IEP_Marking",
    }

    # Forms that are not uniquely identified by their name and are created
    # in the namespace of their parent
    form_properties["namespaced_properties"] = {
        "Civic_Location",
        "Command",
        "Contact_Information",
        "External_Reference",
        "GPS_Location",
        "Signature",
        "Variable",
    }

    # Forms that are not uniquely identified by their name and are created
    # in the namespace of their parent object
    form_properties["object_namespace_properties"] = {
        "Civic_Location",
        "Command",
        "Contact_Information",
        "External_Reference",
        "GPS_Location",
        "Variable",
    }

    # Forms that are not uniquely identified by their name and are created
    # in the namespace of their parent playbook
    form_properties["playbook_namespace_properties"] = {
        "Signature",
        "Variable",
    }

    tlp_levels = {
        0 : "TLP:WHITE",
        1 : "TLP:GREEN",
        2 : "TLP:AMBER",
        3 : "TLP:RED",
    }

    
    # Create a mapping from form to name
    form_to_name = dict()

    # Special cases where the name is chosen differently
    for form in form_properties["steps"]:
        form_to_name[form] = "Steps"
    for form in form_properties["targets"]:
        form_to_name[form] = "Targets"
    for form in form_properties["data_markings"]:
        form_to_name[form] = "Data Markings"
    form_to_name["Playbook"] = "SAPPAN Playbook"
    form_to_name["Command"] = "Commands"

    # Default case
    for form in form_properties["CACAO"]:
        if form in form_to_name:
            continue
        form_to_name[form] = form.replace("_", " ") + "s"
    for form in form_properties["SAPPAN"]:
        if form in form_to_name:
            continue
        form_to_name[form] = form.replace("_", " ") + "s"

    form_to_initial = {
        "GPS_Location" : {},
        "Group_Target" : {
            "type" : "group"
        },
        "HTTP_API_Target" : {
            "type" : "http-api"
        },
        "IEP_Marking" : {
            "type" : "marking-iep"
        },
        "If_Condition_Step" : {
            "type" : "if-condition"
        },
        "Individual_Target" : {
            "type" : "individual"
        },
        "Kali_Linux_Target" : {
            "type" : "kali"
        },
        "Location_Target" : {
            "type" : "location"
        },
        "Organization_Target" : {
            "type" : "organization"
        },
        "Parallel_Step" : {
            "type" : "parallel"
        },
        "Playbook_Step" : {
            "type" : "playbook"
        },
        "Sector_Target" : {
            "type" : "sector"
        },
        "Security_Infrastructure_Category_Target" : {
            "type" : "security-infrastructure-category"
        },
        "Signature" : {
            "type" : "signature"
        },
        "Single_Action_Step" : {
            "type" : "single"
        },
        "SSH_CLI_Target" : {
            "type" : "ssh"
        },
        "Start_Step" : {
            "type" : "start"
        },
        "Statement_Marking" : {
            "type" : "marking-statement"
        },
        "Switch_Condition_Step" : {
            "type" : "switch-condition"
        },
        "TLP_Marking" : {
            "type" : "marking-tlp"
        },
        "Variable" : {
            "type" : "string"
        },
        "While_Condition_Step" : {
            "type" : "while-condition"
        },
        "Attack_Agent_Target" : {
            "type" : "attack-agent"
        },
        "Attack_Group_Target" : {
            "type" : "attack-group"
        },
        "Attacker_Target" : {
            "type" : "attacker"
        },
        "CACAO_Playbook" : {
            "type" : "playbook"
        },
        "Civic_Location" : {
        },
        "Command" : {
            "type" : "manual"
        },
        "End_Step" : {
            "type" : "end"
        },
        "Extension" : {
            "type" : "extension-definition"
        },
        "General_Network_Address_Target" : {
            "type" : "net-address"
        },
    }

    
    def __new__(cls):
        """Override __new__ to make this a singleton class"""
        if not hasattr(cls, 'instance'):
            cls.instance = super(KnowledgeBase, cls).__new__(cls)
        return cls.instance
    

    @classmethod
    def get_name_template(cls, **kwargs) -> str:
        """Returns the name template for the given parents"""
        object_name = kwargs.get('object_name', '')
        object_form = kwargs.get('object_form')
        parent_pb = kwargs.get('parent_playbook', None)
        parent_pbo = list(kwargs.get('parent_objects', []))
        if not parent_pb:
            return object_name
        if object_form in cls.form_properties["namespaced_properties"]:
            if object_form in cls.form_properties["object_namespace_properties"]:
                return f"{parent_pbo[-1].name}: {object_name}"
            elif object_form in cls.form_properties["playbook_namespace_properties"]:
                return f"{parent_pb.name}: {object_name}"
        return object_name
    
    @classmethod
    def get_all_forms(cls):
        """Return a list of all forms"""
        return list(cls.form_properties["SAPPAN"]) + list(cls.form_properties["CACAO"])

    def get_new_object_form_list(self, ref_object_form, headers = False):
        """Return a list of forms for creating a new object"""
        if ref_object_form == 'index':
            forms = list({wiki_name(x) for x in self.form_properties["playbook"]})
            if headers:
                return {
                    "All" : forms
                }
            else:
                return forms
        elif ref_object_form in self.form_properties["playbook"]:
            if wiki_name(ref_object_form) == "CACAO Playbook":
                if headers:
                    form_ordered_list = dict()
                    form_ordered_list["Misc"] = set(self.form_properties["CACAO"])
                    form_ordered_list["Steps"] = form_ordered_list["Misc"] & set(self.form_properties["steps"])
                    form_ordered_list["Misc"] -= form_ordered_list["Steps"]
                    form_ordered_list["Targets"] = form_ordered_list["Misc"] & set(self.form_properties["targets"])
                    form_ordered_list["Misc"] -= form_ordered_list["Targets"]
                    form_ordered_list["Markings"] = form_ordered_list["Misc"] & set(self.form_properties["data_markings"])
                    form_ordered_list["Misc"] -= form_ordered_list["Markings"]
                    form_ordered_list["Misc"] = list(form_ordered_list["Misc"])
                    return form_ordered_list
                else:
                    return list(self.form_properties["CACAO"])
            elif ref_object_form == "Playbook":
                if headers:
                    return {"All": list(self.form_properties["SAPPAN"])}
                else:
                    return list(self.form_properties["SAPPAN"])
        elif ref_object_form in self.form_properties["CACAO"]:
                if headers:
                    form_ordered_list = dict()
                    form_ordered_list["Misc"] = set(self.form_properties["CACAO"])
                    form_ordered_list["Steps"] = form_ordered_list["Misc"] & set(self.form_properties["steps"])
                    form_ordered_list["Misc"] -= form_ordered_list["Steps"]
                    form_ordered_list["Targets"] = form_ordered_list["Misc"] & set(self.form_properties["targets"])
                    form_ordered_list["Misc"] -= form_ordered_list["Targets"]
                    form_ordered_list["Markings"] = form_ordered_list["Misc"] & set(self.form_properties["data_markings"])
                    form_ordered_list["Misc"] -= form_ordered_list["Markings"]
                    form_ordered_list["Misc"] = list(form_ordered_list["Misc"])
                    return form_ordered_list
                else:
                    return list(self.form_properties["CACAO"])
        elif ref_object_form in self.form_properties["SAPPAN"]:
            if headers:
                return {"All": list(self.form_properties["SAPPAN"])}
            else:
                return list(self.form_properties["SAPPAN"])
        else:
            if headers:
                return {"All": self.get_all_forms()}
            else:
                return self.get_all_forms()

    def compare_wiki_title(self,title1:str, title2:str) -> bool:
        """Compares two wiki titles and returns true if they are the same
        Useful because wiki titles can automatically capitalize the first letter and replace spaces with underscores
        """
        return title1.replace(" ","_").lower() == title2.replace(" ","_").lower()
    
    @staticmethod
    def sort_func_playbook_objects_sidebar(obj_header:str) -> int:
        """Determines the order of objects in the sidebar, called by python's sort(ed) function

        Args:
            obj (str): The header to be sorted
        Returns:
            int: The order of the header
        """
        
        # self.form_to_name["Playbook"] = "SAPPAN Playbook"
        # for form in self.form_properties["steps"]:
        #     self.form_to_name[form] = "Steps"
        # self.form_to_name["Command"] = "Commands"
        # for form in self.form_properties["data_markings"]:
        #     self.form_to_name[form] = "Data Markings"
        # for form in self.form_properties["targets"]:
        #     self.form_to_name[form] = "Targets"

        if obj_header=="SAPPAN Playbook":
            return 0
        elif obj_header=="CACAO Playbook":
            return 0
        elif obj_header=="Steps":
            return 1
        elif obj_header=="Commands":
            return 2
        elif obj_header=="Data Markings":
            return 3
        elif obj_header=="Targets":
            return 4
        elif obj_header=="Misc":
            return 9999
        else:
            return 1000
    