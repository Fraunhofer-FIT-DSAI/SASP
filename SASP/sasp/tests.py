from django.test import TestCase, Client
from django.urls import reverse

from sasp.models import Playbook, Playbook_Object, Semantic_Relation
import sasp.management.commands.make_default_user
import sasp.models.cacao_1_1
import sasp.auth.keycloak_integration

import json

# Create your tests here.
# NOTE: Be careful running tests that involve writing or reading from the wiki, we don't have an easy solution to
# reset that environment.

class TestViews(TestCase):
    def setUp(self) -> None:
        # Setup the default user
        make_default_user = sasp.management.commands.make_default_user.Command()
        make_default_user.handle()
        # Create a test playbook
        self.test_playbook = Playbook(
            wiki_page_name="Test Playbook",
            name="Test Playbook",
            wiki_form="CACAO 1-1 Playbook"
        )
        root_object = Playbook_Object(
            wiki_page_name=self.test_playbook.wiki_page_name,
            name=self.test_playbook.name,
            playbook=self.test_playbook,
            wiki_form=self.test_playbook.wiki_form
        )
        root_object:sasp.models.cacao_1_1.CACAO_1_1_Playbook = root_object.resolve_subclass()
        for field in root_object.get_fields():
            initial_value = field.initial_fill(root_object)
            # print(f"Setting {field.field_name} to {initial_value}(type: {type(initial_value)})")
            if initial_value is not None:
                field.set_field(root_object, initial_value)
        self.test_playbook.save()
        root_object.save()
        
        sasp.auth.keycloak_integration.BYPASS_KEYCLOAK = True
        self.client = Client()
    
    def tearDown(self) -> None:
        self.test_playbook.resolve_subclass().remove()
    
    def runTest(self) -> None:
        cl = self.client
        views = [
            ("Index", reverse("index"), 200),
            ("Playbook Detail", reverse("playbook-detail", args=[self.test_playbook.pk]), 200),
            ("Playbook Edit", reverse("playbook-edit", args=[self.test_playbook.pk]), 200),
            ("Playbook BPMN", reverse("playbook-bpmn", args=[self.test_playbook.pk]), 200),
            ("Sharing Json Validator", reverse("sharing-json-validator"), 200),
            ("Sharing Import Json CACAO 1-1", reverse("sharing-import-json-cacao-1-1"), 200),
            ("Sharing Export Json CACAO 1-1", reverse("sharing-export-json-cacao-1-1"), 200),
        ]
        for view_name, url, status_code in views:
            response = cl.get(url)
            self.assertEqual(response.status_code, status_code, f"Failed to load view {view_name} at {url}")

# class TestCacao11Json(TestCase):
#     def setUp(self) -> None:
#         # Setup the default user
#         make_default_user = sasp.management.commands.make_default_user.Command()
#         make_default_user.handle()
        
#     def test_json_validation(self):
#         json_str = """{"type": "playbook", "spec_version": "1.1", "id": "playbook--93abbe83-a306-4b36-9784-bc8d5b807bdd", "name": "Automated Actions Playbook", "playbook_types": ["investigation"], "created_by": "identity--93abbe83-a306-4b36-9784-bc8d5b807bdd", "created": "2024-07-10T12:34:00Z", "modified": "2024-07-10T12:34:00Z", "revoked": true, "workflow_start": "step--66c100ee-3aa6-4ae1-8d18-c5cb6c5f5705", "workflow_exception": "step--ade7e943-db35-4625-ab1e-206f2c585e75", "workflow": {"step--79b6276a-e875-4255-b9ef-02050aa09206": {"type": "if-condition", "name": "ifcondition - Read result", "on_completion": "step--1d7d7912-05b0-43c0-88a5-ff415d8c9336", "condition": "[hive-analyzer-result-by-step:step--12e96281-cdff-4ca7-8895-1e7f42da4cbd[0].report.success = true]", "on_true": ["step--5195d65e-dd06-48f3-a430-ae90ef10dd92"], "on_false": ["step--1d7d7912-05b0-43c0-88a5-ff415d8c9336"]}, "step--12e96281-cdff-4ca7-8895-1e7f42da4cbd": {"type": "single", "name": "single - Evaluate Observable", "on_completion": "step--79b6276a-e875-4255-b9ef-02050aa09206", "commands": [{"type": "openc2-json", "command": "{\\n    \\"action\\": \\"start\\",\\n    \\"target\\": {\\n        \\"uri\\": \\"VirusTotal_GetReport_3_1\\"\\n    },\\n    \\"args\\": {\\n        \\"observable\\": \\"hive-case-observable:exHash\\"\\n    }\\n}"}]}, "step--5195d65e-dd06-48f3-a430-ae90ef10dd92": {"type": "single", "name": "single - Manual response required", "commands": [{"type": "manual", "command": "Review response and take action"}]}, "step--66c100ee-3aa6-4ae1-8d18-c5cb6c5f5705": {"type": "start", "name": "start - case arrives", "on_completion": "step--12e96281-cdff-4ca7-8895-1e7f42da4cbd"}, "step--1d53dca2-e5a7-417d-8c26-91bc4d94c5dd": {"type": "end", "name": "end - End of incident"}, "step--1d7d7912-05b0-43c0-88a5-ff415d8c9336": {"type": "end", "name": "end - No action required"}, "step--ade7e943-db35-4625-ab1e-206f2c585e75": {"type": "end", "name": "end - Exception occurred"}}}"""
#         json_data = json.loads(json_str)
#         deserializer = sasp.models.cacao_1_1.CACAO_1_1.Deserializer(json_data)
#         valid, errors = deserializer.validate()
#         for msg, level, context in errors:
#             print(f"{level}: {msg}")
#             if context and len(context) == 3:
#                 # print(context[0]) # Holds the full context so we don't need to print it
#                 print(context[1])
#                 print(context[2])
#         print(valid)
    
#     def test_json_import(self, with_save=True):
#         json_data = json.loads(
#             r"""{"type":"playbook","spec_version":"1.1","id":"playbook--93abbe83-a306-4b36-9784-bc8d5b807bdd","name":"Test Playbook UniqueString416745134","playbook_types":["investigation"],"created_by":"identity--93abbe83-a306-4b36-9784-bc8d5b807bdd","created":"2024-07-10T12:34:00Z","modified":"2024-07-10T12:34:00Z","revoked":true,"workflow_start":"step--ffc100ee-3aa6-4ae1-8d18-c5cb6c5f5705","workflow_exception":"step--ffe7e943-db35-4625-ab1e-206f2c585e75","workflow":{"step--ffb6276a-e875-4255-b9ef-02050aa09206":{"type":"if-condition","name":"ifcondition - Read result","on_completion":"step--ff7d7912-05b0-43c0-88a5-ff415d8c9336","condition":"[hive-analyzer-result-by-step:step--ffe96281-cdff-4ca7-8895-1e7f42da4cbd[0].report.success = true]","on_true":["step--ff95d65e-dd06-48f3-a430-ae90ef10dd92"],"on_false":["step--ff7d7912-05b0-43c0-88a5-ff415d8c9336"]},"step--ffe96281-cdff-4ca7-8895-1e7f42da4cbd":{"type":"single","name":"single - Evaluate Observable","on_completion":"step--ffb6276a-e875-4255-b9ef-02050aa09206","commands":[{"type":"openc2-json","command":"{\n    \"action\": \"start\",\n    \"target\": {\n        \"uri\": \"VirusTotal_GetReport_3_1\"\n    },\n    \"args\": {\n        \"observable\": \"hive-case-observable:exHash\"\n    }\n}"}]},"step--ff95d65e-dd06-48f3-a430-ae90ef10dd92":{"type":"single","name":"single - Manual response required","commands":[{"type":"manual","command":"Review response and take action"}]},"step--ffc100ee-3aa6-4ae1-8d18-c5cb6c5f5705":{"type":"start","name":"start - case arrives","on_completion":"step--ffe96281-cdff-4ca7-8895-1e7f42da4cbd"},"step--ff53dca2-e5a7-417d-8c26-91bc4d94c5dd":{"type":"end","name":"end - End of incident"},"step--ff7d7912-05b0-43c0-88a5-ff415d8c9336":{"type":"end","name":"end - No action required"},"step--ffe7e943-db35-4625-ab1e-206f2c585e75":{"type":"end","name":"end - Exception occurred"}}}"""
#         )
#         deserializer = sasp.models.cacao_1_1.CACAO_1_1.Deserializer(json_data)
#         deserializer.deserialize()
#         self.assertEqual(deserializer.objects.__len__(), 10)
#         self.assertIsNotNone(deserializer.playbook)
#         if with_save:
#             deserializer.save()
#             self.assertIsNotNone(deserializer.playbook.pk)
#             self.assertEqual(len(Playbook.objects.filter(pk=deserializer.playbook.pk)), 1)
#             self.assertEqual(len(Playbook_Object.objects.filter(playbook=deserializer.playbook.pk)), 10)
#             self.assertEqual(len(Semantic_Relation.objects.filter(playbook=deserializer.playbook.pk)), 16)
#             pb = sasp.models.Playbook.query(wiki_page_name="Test Playbook UniqueString416745134").first()
#             pb:sasp.models.cacao_1_1.CACAO_1_1 = pb.resolve_subclass()
#             pb.remove()
    
#     @staticmethod
#     def test_wiki_form_creation():
#         import sasp.wiki_forms
#         sasp.wiki_forms.WikiFormManager.update_wiki(dry_run=True)