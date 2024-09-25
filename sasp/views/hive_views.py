from typing import Any
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import (
    HttpResponseRedirect,
)
from ..auth.keycloak_integration import keycloak_login_required, KeycloakLoginRequiredMixin
from ..models import (
    Playbook,
    Automation_Instance,
)
from ..forms import (
    HiveDashboardForm,
)
from ..external_apis.hive_cortex_api import CortexApi, HiveAPI
from ..automation_component.hive_playbook_instances import spawn_workflow

import sasp.views as views
from sasp.knowledge import KnowledgeBase as kb


from . import logger

import json

@keycloak_login_required
def TheHiveDashboard(request):
    # Disabled for this version
    messages.error(request, _("TheHive Dashboard is currently disabled"))
    return HttpResponseRedirect(reverse("index"))

    hiveAPI = HiveAPI()
    cortexAPI = CortexApi()
    context = views.SASPCommonView().get_context_data()
    context.update({
        "logged_in": hiveAPI.logged_in,
        "cortex_logged_in": cortexAPI.logged_in,
    })
    available_playbooks = Playbook.objects.all()

    def prepare_context():
        # Get the case list and prepare the context
        context["title"] = "TheHive Dashboard"
        context["help_text"] = kb.help_texts.thehive.dashboard__OBJ()
        case_list = hiveAPI.get_open_cases().json()
        active_case_ids = {
            aut_instance.case_id
            for aut_instance in Automation_Instance.objects.filter(status="In Progress")
        }
        if None in active_case_ids:
            logger.error(
                "None in active_case_ids (Not critical, but should not happen)"
            )
            active_case_ids.remove(None)

        context["case_list"] = [
            {
                "caseID": case.get("_id", "NaN"),
                "title": case.get("title", "NaN"),
                "description": case.get("description", "NaN"),
                "createdBy": case.get("createdBy", "NaN"),
                "updatedBy": case.get("updatedBy", "NaN"),
                "tags": ", ".join(case.get("tags", [])),
                "idx": f"case{i}",
                "href": f"{hiveAPI.url}/index.html#{'!'}/case/~{case.get('_id', 'NaN')}/details",
            }
            for i, case in enumerate(case_list)
            if case.get("caseId") not in active_case_ids
        ]
        for case in context["case_list"]:
            for key, value in case.items():
                if isinstance(value, str) and len(value) > 100:
                    case[key] = value[:100] + "..."
        context["playbook_list"] = [
            {
                "name": playbook.get_label(),
                "wiki_page_name": playbook.wiki_page_name,
                "tags": ", ".join(playbook.get_tags()),
                "href": reverse("playbook-detail", args=[playbook.pk]),
                "idx": f"playbook{i}",
            }
            for i, playbook in enumerate(available_playbooks)
        ]
        context["active_runs_list"] = [
            {
                "playbook_id": aut_instance.playbook.get_label(),
                "case_id": aut_instance.case_id,
                "status": aut_instance.status,
                "started": aut_instance.started,
                "last_update": aut_instance.last_update,
                "completed": aut_instance.completed,
                "href": reverse("thehive-run-details", args=[aut_instance.pk]),
                "idx": f"run{i}",
            }
            for i, aut_instance in enumerate(
                Automation_Instance.objects.all().order_by("-last_update")
            )
        ]

    def prepare_form():
        # Get the form
        if request.method == "POST":
            form_ = HiveDashboardForm(
                request.POST,
                playbook_choices=available_playbooks,
                case_choices=context["case_list"],
            )
        else:
            form_ = HiveDashboardForm(
                playbook_choices=available_playbooks, case_choices=context["case_list"]
            )

        context["form"] = form_
        return form_

    if not hiveAPI.logged_in:
        return render(request, "thehive_dashboard.html", context=context)
    else:
        prepare_context()
        if request.method == "POST":
            form = prepare_form()
            if form.is_valid():
                return HttpResponseRedirect(
                    reverse(
                        "thehive-run-playbook",
                        kwargs={
                            "playbook_id": form.cleaned_data["playbook_choice"],
                            "case_id": form.cleaned_data["case_choice"],
                        },
                    )
                )
            else:
                return render(request, "thehive_dashboard.html", context=context)
        else:
            form = prepare_form()

            return render(request, "thehive_dashboard.html", context=context)


@keycloak_login_required
def TheHiveRunPlaybook(request, playbook_id, case_id):
    # Disabled for this version
    messages.error(request, _("TheHive Dashboard is currently disabled"))
    return HttpResponseRedirect(reverse("index"))

    db_object = spawn_workflow(
        playbook=Playbook.objects.get(pk=playbook_id), case_id=case_id
    )
    return HttpResponseRedirect(
        reverse(
            "thehive-run-details",
            kwargs={
                "pk": db_object.pk,
            },
        )
    )


@keycloak_login_required
def deleteTheHiveRun(request, pk):
    # Disabled for this version
    messages.error(request, _("TheHive Dashboard is currently disabled"))
    return HttpResponseRedirect(reverse("index"))

    instance = get_object_or_404(Automation_Instance, pk=pk)
    instance.delete()
    return HttpResponseRedirect(reverse("thehive-dashboard"))

class TheHiveRunDetails(KeycloakLoginRequiredMixin,views.SASPBaseDetailView):
    model = Automation_Instance
    template_name = "thehive_run_details.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Disabled for this version
        messages.error(request, _("TheHive Dashboard is currently disabled"))
        return HttpResponseRedirect(reverse("index"))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super(TheHiveRunDetails, self).get_context_data(**kwargs)
        context["help_text"] = kb.help_texts.thehive.run__OBJ()
        context['json_render_data'] = dict()
        run_info = self.object.get_run_info()
        execution_details = json.loads(run_info["json_representation"])
        context["playbook_id"] = run_info["playbook"]
        context["case_id"] = run_info["case_id"]
        context["playbook_status"] = run_info["status"]

        js_context = dict()
        js_context["confirm_delete"] = {}
        js_context["confirm_delete"]["delete_button"] = {
            'message': 'Are you sure you want to delete this run?',
            'url': reverse('thehive-delete-run', kwargs={'pk': self.object.pk}),
        }
        context['js_context'] = js_context

        # Convention: [Header, Value, optional: switch for custom rendering, optional: custom data depending on switch]
        context["active_steps"] = list()
        workflow = execution_details.get("workflow", dict())

        # Active steps to be displayed
        context['step_overview_theaders'] = ['Name', 'Status', 'Json Representation']
        for step in workflow:
            if workflow[step].get("status", None) == "In Progress":
                context["active_steps"].append([
                    workflow[step].get("name", step),
                    ['Status', workflow[step].get("status", None)],
                    [
                        'Json Representation', 
                        json.dumps(workflow[step], indent=4),
                        "json", # Switch to tell template
                        "json-{}".format(len(context['json_render_data'])), # Field id for js to render
                    ],
                ]
                )
                context['json_render_data'][f"json-{len(context['json_render_data'])}"] = {
                    'data' : workflow[step],
                    'options' : {'collapsed': True},
                }
        
        # Active steps to be displayed from branch workflows
        # for idx,iteration in execution_details.get("iterations", dict()).items():
        #     workflow = iteration.get("branch_workflow", dict())
        #     for step in workflow:
        #         if workflow[step].get("status", None) == "In Progress":
        #             context["active_steps"][f"{idx}-{step}"] = workflow[step]
                
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
            json_id = f"json-{len(context['json_render_data'])}"
            context["json_render_data"][json_id] = {
                'data' : json.loads(confirmation_requests[key]['data']),
                'options' : {'collapsed': False},
            }
            confirmation_requests[key]['data_field_id'] = json_id
            confirmation_requests[key]['confirm_url'] = reverse('thehive-confirm-request', kwargs={'pk': self.object.pk, 'uuid': key, 'action': 'confirm'})
        
        context['confirmation_requests'] = confirmation_requests

        context['json_render_data']['run-details'] = {
            'data' : execution_details,
            'options' : {},
        }
        context['run_details'] = json.dumps(execution_details, indent=4)
        context[
            "title"
        ] = f"Run details for playbook {context['playbook_id']} in case {context['case_id']}"
        return context

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
    return HttpResponseRedirect(reverse('thehive-run-details', kwargs={'pk': pk}))