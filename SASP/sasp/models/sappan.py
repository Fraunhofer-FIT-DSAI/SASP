from . import Playbook

class SAPPAN(Playbook):
    wiki_form = "SAPPAN Playbook"
    class Meta:
        proxy = True
    
    # def bark(self):
    #     print('CACAO_1_1 bark')
    #     print(self.a_new_attribute)
    #     print(self.name)
    
    def get_new_objects(self) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return []

    def get_confidentiality(self):
        confidentiality = self.content.get("HasConfidentiality", ["a - TLP:WHITE"])
        return {
            'a - tlp:white': 'TLP:WHITE',
            'b - tlp:green': 'TLP:GREEN',
            'c - tlp:amber': 'TLP:AMBER',
            'd - tlp:red': 'TLP:RED',
        }[confidentiality[0].strip().lower()]

    def get_cls_label(self):
        """Returns a human readable label for the form of the playbook."""
        return "SAPPAN Playbook"
    
    def export_to_json(self, **kwargs):
        # Json string or None, Errors
        raise NotImplementedError("Export to JSON not implemented for SAPPAN Playbooks.")
    
    def add_to_field(self, field_name, value):
        self.content[field_name] = self.content.get(field_name, []) + [value]
    
    def initial_fill(self):
        return {}
    
    def register_object(self, object):
        """Registers an object with the playbook."""
        if object.wiki_form == "Initial Step":
            self.content["hasInitialStep"] = self.content.get("hasInitialStep", []) + [object.wiki_page_name]
        elif object.wiki_form == "Final Step":
            self.content["hasFinalStep"] = self.content.get("hasFinalStep", []) + [object.wiki_page_name]
        elif object.wiki_form == "Intermediate Step":
            self.content["hasIntermediateStep"] = self.content.get("hasIntermediateStep", []) + [object.wiki_page_name]
        elif object.wiki_form == "Optional Step":
            self.content["hasOptionalStep"] = self.content.get("hasOptionalStep", []) + [object.wiki_page_name]

    def bpmn(self):
        return None, ["BPMN Generation not implemented for SAPPAN Playbooks."]