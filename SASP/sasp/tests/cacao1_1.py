from django.test import TransactionTestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse

from sasp.models import Playbook, Automation_Instance
from sasp.forms.automation import AutomationPlaybookSelectForm, AutomationContextFormCACAO_1_1
import sasp.management.commands.make_default_user
import sasp.models.cacao_1_1 as cacao_1_1
import sasp.auth.keycloak_integration

from pathlib import Path
import json
import time

resource_path = Path(__file__).parent / "resources"


class TestCACAO1_1(TransactionTestCase):
    def setUp(self) -> None:
        # Setup the default user
        make_default_user = sasp.management.commands.make_default_user.Command()
        make_default_user.handle()
        
        self.user = User.objects.get(username="default")
        
        cacao_1_1.CACAO_1_1.new_from_json(self.json_playbook_automated_actions_manual)
        self.playbook: cacao_1_1.CACAO_1_1 = Playbook.objects.first().resolve_subclass()
        
        self.requestFactory = RequestFactory()
        sasp.auth.keycloak_integration.BYPASS_KEYCLOAK = True

    @classmethod
    def tearDownClass(cls) -> None:
        for playbook in Playbook.objects.all():
            playbook.resolve_subclass().remove()

    def test_import(self):
        self.assertEqual(Playbook.objects.count(), 1)

    def test_export(self):
        json_data = self.playbook.serialize()
        self.assertEqual(json_data, self.json_playbook_automated_actions_manual)
        
    def test_forms(self):
        playbook_select_form = AutomationPlaybookSelectForm()
        # Test field playbook, make sure the playbook is in the queryset
        self.assertEqual(playbook_select_form.fields["playbook"].queryset.count(), 1)
        self.assertEqual(playbook_select_form.fields["playbook"].queryset.first(), self.playbook)
        request = self.requestFactory.post("/", {"playbook": self.playbook.pk})
        playbook_select_form = AutomationPlaybookSelectForm(request.POST)
        self.assertEqual(playbook_select_form.is_valid(), True)
        
        request = self.requestFactory.get("/")
        request.user = self.user
        playbook_context_form = AutomationContextFormCACAO_1_1(playbook=self.playbook, request=request)
        self.assertEqual(len(playbook_context_form.fields), 2)
        self.assertIn("hive_case", playbook_context_form.fields)
        self.assertIn("workflow_var_var_int", playbook_context_form.fields)
        request = self.requestFactory.post("/", {"hive_case": "", "workflow_var_var_int": 1})
        request.user = self.user
        playbook_context_form = AutomationContextFormCACAO_1_1(request.POST, playbook=self.playbook, request=request)
        valid = playbook_context_form.is_valid()
        self.assertEqual(valid, True)
        produced_context = playbook_context_form.get_automation_context()
        compare_context = {
            'hive_case_id': None,
            'hive_case_name': None,
            'workflow_vars': {
                "$$var_int$$" : {
                    "var_id": "$$var_int$$",
                    "var_type": "integer",
                    "var_value": 1,
                    "var_constant": True,
                }
            },
            'step_vars': {},
            'global_vars': {},
        }
        self.assertEqual(produced_context, compare_context)

    def test_automation_manual(self):
        automation = self.playbook.Automation(self.playbook)
        self.assertEqual(automation.ready(), True)

        context = automation.get_context()
        db_obj = cacao_1_1.CACAO_1_1.Automation.execute(self.playbook, context)

        start = time.time()
        while True:
            if time.time() - start > 10:
                self.fail("Timeout")

            # Save debug information to variables for inspection
            status = db_obj.status
            match status:
                case Automation_Instance.Status.RUNNING.value:
                    if db_obj.confirmation_requests:
                        for confirmation_request in db_obj.confirmation_requests:
                            db_obj.approve_confirmation_request(confirmation_request)
                case (
                    Automation_Instance.Status.COMPLETED.value
                    | Automation_Instance.Status.ERROR.value
                    | Automation_Instance.Status.CANCELED.value
                ):
                    break
                case Automation_Instance.Status.INITIALIZED.value:
                    pass
                case _:
                    self.fail(f"Unexpected status: {status}")
            time.sleep(1)
            db_obj.refresh_from_db()
        self.assertEqual(db_obj.status, Automation_Instance.Status.COMPLETED.value)
    
    def test_automation_bpmn(self):
        automation = self.playbook.Automation(self.playbook)
        self.assertEqual(automation.ready(), True)

        context = automation.get_context()
        db_obj = cacao_1_1.CACAO_1_1.Automation.execute(self.playbook, context)

        start = time.time()
        while True:
            if time.time() - start > 10:
                self.fail("Timeout")

            # Save debug information to variables for inspection
            status = db_obj.status
            match status:
                case Automation_Instance.Status.RUNNING.value:
                    if db_obj.confirmation_requests:
                        bpmn_xml, error_list = self.playbook.Automation.get_bpmn(db_obj)
                        self.assertEqual(len(error_list), 0)
                        self.assertIsNotNone(bpmn_xml)
                        self.assertGreater(len(bpmn_xml), 0)
                        for confirmation_request in db_obj.confirmation_requests:
                            db_obj.approve_confirmation_request(confirmation_request)
                case (
                    Automation_Instance.Status.COMPLETED.value
                    | Automation_Instance.Status.ERROR.value
                    | Automation_Instance.Status.CANCELED.value
                ):
                    break
                case Automation_Instance.Status.INITIALIZED.value:
                    pass
                case _:
                    self.fail(f"Unexpected status: {status}")
            time.sleep(1)
            db_obj.refresh_from_db()
        bpmn_xml, error_list = self.playbook.Automation.get_bpmn(db_obj)
        self.assertEqual(len(error_list), 0)
        self.assertIsNotNone(bpmn_xml)
        self.assertGreater(len(bpmn_xml), 0)


    def test_automation_manual_timeout(self):
        # Same as test_automation_manual, but we don't approve the confirmation request and wait for timeout
        automation = self.playbook.Automation(self.playbook)
        self.assertEqual(automation.ready(), True)

        context = automation.get_context()
        db_obj = cacao_1_1.CACAO_1_1.Automation.execute(self.playbook, context)

        start = time.time()
        while True:
            if time.time() - start > 15:
                self.fail("Timeout")

            # Save debug information to variables for inspection
            status = db_obj.status
            match status:
                case (
                    Automation_Instance.Status.COMPLETED.value
                    | Automation_Instance.Status.ERROR.value
                    | Automation_Instance.Status.CANCELED.value
                ):
                    break
                case (
                    Automation_Instance.Status.INITIALIZED.value
                    | Automation_Instance.Status.RUNNING.value
                ):
                    pass
                case _:
                    self.fail(f"Unexpected status: {status}")
            time.sleep(1)
            db_obj.refresh_from_db()
        self.assertEqual(db_obj.status, Automation_Instance.Status.COMPLETED.value)
    
    def test_automation_views(self):
        # Open the automation dashboard
        response = self.client.get(reverse("automation-dashboard"))
        self.assertEqual(response.status_code, 200)
        
        # Open the automation context form
        response = self.client.post(reverse("automation-dashboard"), {"playbook": self.playbook.pk})
        # Redirects to the context form
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("automation-context-form", args=[self.playbook.pk]))
        self.assertEqual(response.status_code, 200)
        # Post the context form
        response = self.client.post(reverse("automation-context-form", args=[self.playbook.pk]), {"hive_case": "", "workflow_var_var_int": 10})
        self.assertEqual(response.status_code, 302)
        # Redirects to the run details
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        # Confirm the request
        auto_instance = response.context_data["automation_instance"]
        response = None
        for _ in range(5):
            try:
                auto_instance.refresh_from_db()
                confirmation_request = list(auto_instance.confirmation_requests.keys())[0]
                response = self.client.get(reverse("automation-confirm-request", args=[auto_instance.pk, confirmation_request, "approve"]))
                break
            except Exception:
                time.sleep(1)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        
        i = 0
        while not auto_instance.completed:
            auto_instance.refresh_from_db()
            i += 1
            if i > 10:
                self.fail("Timeout")
            time.sleep(1)
        
        # Delete the automation run (confirmation page)
        response = self.client.get(reverse("automation-delete-run", args=[auto_instance.pk]))
        self.assertEqual(response.status_code, 200)
        # Delete the automation run
        response = self.client.get(reverse("automation-delete-run", args=[auto_instance.pk])+"?confirm")
        self.assertEqual(response.status_code, 302)

    # Load the JSON files
    json_playbook_automated_actions = json.loads(
        (resource_path / "cacao_1_1_playbook_automated_actions.json").read_text()
    )
    json_playbook_automated_actions_manual = json.loads(
        (resource_path / "cacao_1_1_playbook_automated_actions_manual.json").read_text()
    )
