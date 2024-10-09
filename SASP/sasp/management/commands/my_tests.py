from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # self.test_json_validation()
        # self.test_json_import()
        self.test_json_import(with_save=True)
        # self.test_wiki_form_creation()

    @staticmethod
    def test_json_validation():
        import json
        from pathlib import Path
        import sasp.models.cacao_1_1
        
        json_file = Path(__file__).parent / '../../../example playbooks/Automated Actions Playbook.json'
        assert json_file.exists()
        json_data = json.loads(json_file.read_text())
        deserializer = sasp.models.cacao_1_1.CACAO_1_1.Deserializer(json_data)
        valid, errors = deserializer.validate()
        for msg, level, context in errors:
            print(f"{level}: {msg}")
            if context and len(context) == 3:
                # print(context[0]) # Holds the full context so we don't need to print it
                print(context[1])
                print(context[2])
        print(valid)
    
    @staticmethod
    def test_json_import(with_save=False):
        import json
        from pathlib import Path
        import sasp.models.cacao_1_1
        from sasp.models import Playbook
        
        Playbook.objects.all().delete()
        
        json_file = Path(__file__).parent / '../../../example playbooks/Test Playbook Cacao11.json'
        assert json_file.exists()
        json_data = json.loads(json_file.read_text())
        deserializer = sasp.models.cacao_1_1.CACAO_1_1.Deserializer(json_data)
        deserializer.deserialize()
        print("Set breakpoints here to inspect the deserialized objects")
        for p_object in deserializer.objects:
            print(f"('{p_object.wiki_page_name}', '{p_object.wiki_form}', '{json.dumps(p_object.content,sort_keys=True)}'),")
        if with_save:
            deserializer.save()
            print("Saved playbook.")
            sasp.models.cacao_1_1.CACAO_1_1.objects.get(wiki_page_name="Test Playbook Uniquestring416745134").remove()
    
    @staticmethod
    def test_wiki_form_creation():
        import sasp.wiki_forms
        sasp.wiki_forms.WikiFormManager.update_wiki(dry_run=True)