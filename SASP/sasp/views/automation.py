from typing import Any
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
# escape is imported
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    Http404,
)
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.views import APIView
from rest_framework.response import Response
from ..auth.keycloak_integration import  KeycloakLoginRequiredMixin
from ..models import (
    Playbook,
    Automation_Instance,
)
from sasp.forms.automation import AutomationPlaybookSelectForm, AutomationContextForm
from sasp.external_apis.hive_cortex_api import Hive

import sasp.views as views
from sasp.knowledge import BPMN as bpmn_knowledge


from . import logger

import json

class AutomationDashboard(KeycloakLoginRequiredMixin,views.SASPBaseFormView):
    template_name = "automation_dashboard.html"
    help_text = _("In this screen you can see all active executions of playbooks. You can also start a new execution.")
    form_class = AutomationPlaybookSelectForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super(AutomationDashboard, self).get_context_data(**kwargs)
        context["title"] = _("Playbook Execution Dashboard")
        context["hive_logged_in"] = Hive.HiveAPI(self.request.user) is not None
        context["active_runs_list"] = [
            {
                "playbook_id": aut_instance.playbook.resolve_subclass().get_label(),
                "case_id": aut_instance.case_id or _("None"),
                "status": aut_instance.status_label,
                "started": aut_instance.started,
                "last_update": aut_instance.last_update,
                "completed": aut_instance.completed,
                "href": reverse("automation-run-details", args=[aut_instance.pk]),
                "idx": f"run{i}",
            }
            for i, aut_instance in enumerate(
                Automation_Instance.objects.all().order_by("-last_update")
            )
        ]
        
        if context["hive_logged_in"]:
            case_list = Hive.HiveAPI(self.request.user).get_open_cases()
            active_case_ids = {
                aut_instance.case_id
                for aut_instance in Automation_Instance.objects.filter(status=Automation_Instance.Status.RUNNING.value)
                if aut_instance.case_id
            }

            context["case_list"] = [
                {
                    "caseID": case.get("_id", "NaN"),
                    "title": case.get("title", "NaN"),
                    "description": case.get("description", "NaN"),
                    "createdBy": case.get("_createdBy", "NaN"),
                    "updatedBy": case.get("_updatedBy", "NaN"),
                    "tags": ", ".join(case.get("tags", [])),
                    "idx": f"case{i}",
                }
                for i, case in enumerate(case_list)
                if case.get("_id") not in active_case_ids
            ]
            for case in context["case_list"]:
                for key, value in case.items():
                    if isinstance(value, str) and len(value) > 100:
                        case[key] = value[:100] + "..."
        
        return context
    
    def form_valid(self, form: AutomationPlaybookSelectForm) -> HttpResponse:
        return HttpResponseRedirect(reverse(
            "automation-context-form", 
            kwargs={
                "pk_pb": form.cleaned_data["playbook"].pk}
        ))

class AutomationRunContextView(KeycloakLoginRequiredMixin,views.SASPBaseFormView):
    template_name = "automation_run_gather_context.html"
    help_text = _("Gather Context")
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pass

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super(AutomationRunContextView, self).get_context_data(**kwargs)
        context["title"] = _("Gather Context")
        return context
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.playbook = Playbook.objects.get(pk=self.kwargs['pk_pb'])
            self.playbook:Playbook = self.playbook.resolve_subclass()
        except Playbook.DoesNotExist:
            raise Http404(_("Playbook not found"))
    
    def get_form_class(self):
        """Return the form class to use."""
        return self.playbook.Automation.get_context_form()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['playbook'] = self.playbook
        return kwargs
    
    def form_valid(self, form: AutomationContextForm) -> HttpResponse:
        context = form.get_automation_context()
        try:
            user = self.request.user
            automation_instance = self.playbook.Automation.execute(self.playbook, context, user=user)
            return HttpResponseRedirect(
                reverse("automation-run-details", kwargs={"pk": automation_instance.pk})
            )
        except self.playbook.Automation.AutomationException as e:
            messages.error(self.request, f"Error starting execution: {e}")
            return HttpResponseRedirect(reverse('automation-dashboard'))

class AutomationRunPlaybookBPMN(APIView):
    def get(self, request, pk):
        instance = get_object_or_404(Automation_Instance, pk=pk)
        pb = instance.playbook.resolve_subclass()
        bpmn_xml, error_list = pb.Automation.get_bpmn(instance)
        if error_list:
            return Response({"error": error_list}, status=400)
        response = Response(bpmn_xml)
        return response

class AutomationRunDetails(KeycloakLoginRequiredMixin,views.SASPBaseDetailView):
    model = Automation_Instance
    template_name = "automation_run_details.html"
    help_text = _("Run Details")
    object: Automation_Instance
    

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super(AutomationRunDetails, self).get_context_data(**kwargs)
        run_info = self.object.get_run_info()
        context["run_info"] = json.dumps(run_info, indent=4, cls=DjangoJSONEncoder)
        context["playbook_id"] = run_info["playbook"]
        context["case_id"] = run_info["case_id"]
        context["playbook_status"] = run_info["status"]
        context["topbar"] = {
            "buttons": {
                "extended": {
                    "button-delete": {
                        "type_": "button",
                        "text": _("Delete"),
                        "outline": "danger",
                        "href": reverse("automation-delete-run", kwargs={"pk": self.object.pk}),
                    }
                }
            }
        }

        # Convention: [Header, Value, optional: switch for custom rendering, optional: custom data depending on switch]
        context["output"] = [
            {
                "title": obj["id"],
                "message": obj["messages"][-1] if obj.get("messages") else _("None"),
                "data": json.dumps(obj, indent=4, cls=DjangoJSONEncoder),
            }
            for obj in run_info["output"]
        ]
        
        # Steps currently requiring user input
        confirmation_requests = self.object.confirmation_requests
        confirmation_requests = {
            key: {
                'title': value['title'],
                'message': value['message'],
                'data': json.dumps(value['data'], indent=4),
                'timeout' : value['timeout'],
                'timestamp' : value['timestamp'],
                'approved' : value['approved'],
                'abort' : value['abort'],
            } for key, value in confirmation_requests.items()
        }
        for key in confirmation_requests:
            confirmation_requests[key]['confirm_url'] = reverse('automation-confirm-request', kwargs={'pk': self.object.pk, 'uuid': key, 'action': 'confirm'})
            confirmation_requests[key]['deny_url'] = reverse('automation-confirm-request', kwargs={'pk': self.object.pk, 'uuid': key, 'action': 'deny'})
        
        context['confirmation_requests'] = confirmation_requests
        context["title"] = f"Run details for playbook {context['playbook_id']}"
        if context['case_id'] != "None":
            context["title"] += f" in case {context['case_id']}"
        
        context["execution_active"] = self.object.status == Automation_Instance.Status.RUNNING.value
        
        # BPMN
        pb = self.object.playbook.resolve_subclass()
        bpmn_xml, error_list = pb.Automation.get_bpmn(self.object)
        context["bpmn_xml"] = bpmn_xml
        
        context["bpmn_legend"] = [
            (_("Initialized"), bpmn_knowledge.initatialized_color),
            (_("In Progress"), bpmn_knowledge.in_progress_color),
            (_("Active"), bpmn_knowledge.active_color),
            (_("Success"), bpmn_knowledge.success_color),
            (_("Failed"), bpmn_knowledge.failed_color),
        ]
        context["bpmn_url"] = reverse("api-automation-bpmn", kwargs={"pk": self.object.pk})
        # for error in error_list:
        #     messages.error(self.request, error)
        return context

class AutomationDeleteView(KeycloakLoginRequiredMixin, views.SASPBaseDetailView):
    help_text = "Please confirm that you want to delete this object."
    template_name = "delete_confirm.html"
    model = Automation_Instance
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Delete: ") + str(self.object)
        context["name_deleted_object"] = str(self.object)
        context["data_deleted_object"] = json.dumps(self.object.get_run_info(), indent=4, cls=DjangoJSONEncoder)
        context["confirm_url"] = reverse("automation-delete-run", kwargs={"pk": self.object.pk})+"?confirm"
        return context
    
    def get(self, request, *args, **kwargs):
        if 'confirm' in request.GET:
            return self.delete(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, _("Successfully deleted object"))
        return HttpResponseRedirect(reverse("automation-dashboard"))


def confirm_request(request, pk, uuid, action):
    instance = get_object_or_404(Automation_Instance, pk=pk)
    try:
        if action == 'confirm':
            instance.approve_confirmation_request(uuid)
        elif action == 'deny':
            instance.abort_confirmation_request(uuid)
    except Exception as e:
        logger.error(f"Error while confirming request: {e}")
        messages.error(request, f"Error while confirming request: {e}")
    return HttpResponseRedirect(reverse('automation-run-details', kwargs={'pk': pk}))