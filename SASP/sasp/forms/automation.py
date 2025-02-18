from django import forms
from django.utils.translation import gettext as _
from django.utils.text import slugify
from copy import deepcopy

from sasp.external_apis.hive_cortex_api import Hive
from .form_fields import (
    CustomCharField,
    CustomJSONField,
    CustomModelChoiceField,
    CustomChoiceField,
)
from sasp.models import Playbook


class AutomationPlaybookSelectForm(forms.Form):
    playbook = CustomModelChoiceField(
        label=_("Playbook"), help_text=_("Select a playbook to automate"), queryset=None
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls_forms = [
            cls_.cls_form for cls_ in Playbook.proxyclasses if cls_.Automation.supported
        ]
        # Set the queryset for the playbook field
        self.fields["playbook"].queryset = Playbook.objects.filter(
            wiki_form__in=cls_forms
        )

    def clean_playbook(self):
        playbook: Playbook = self.cleaned_data["playbook"].resolve_subclass()
        if not playbook.Automation.supported:
            raise forms.ValidationError(
                _("Automation is not supported for this playbook")
            )
        auto = playbook.Automation(playbook)

        if not auto.ready():
            messages = []
            error: Playbook.Automation.AutomationException
            for error in auto.ready_errors:
                message = _("Playbook is not ready for automation: \n")
                if error.traceback:
                    message += f"{error.traceback}: "
                if error.field_name:
                    message += f"{error.field_name} - "
                message += error.message
                messages.append(message)
            raise forms.ValidationError(messages)
        return playbook


class AutomationContextForm(forms.Form):
    def get_automation_context(self) -> dict:
        raise NotImplementedError("get_automation_context must be implemented in subclass")


class AutomationContextFormCACAO_1_1(AutomationContextForm):
    hive_case = CustomChoiceField(
        label=_("Hive Case"),
        help_text=_("Select the Hive Case to run the automation on"),
        choices=[("", _("Don't use Hive."))],
        required=False,
    )

    def __init__(self, *args, request=None, playbook:Playbook=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if Hive.HiveAPI(request.user):
            open_cases = Hive.HiveAPI(request.user).get_open_cases()
            choices = self.fields["hive_case"].choices
            choices.extend(
                [
                    (
                        hive_case["_id"],
                        hive_case.get("title", _("Case: %s") % hive_case["_id"]),
                    )
                    for hive_case in open_cases
                    if "_id" in hive_case
                ]
            )
            self.fields["hive_case"].choices = choices
                
        self.playbook_context = playbook.Automation(playbook).get_context()
        # Workflow Vars
        for var in self.playbook_context["workflow_vars"].values():
            self.make_var_field("workflow_var", var)
        # Step Vars
        for step_id, step in self.playbook_context["step_vars"].items():
            for var in step.values():
                self.make_var_field("step_var_" + step_id, var)
    
    def get_automation_context(self) -> dict:
        context = deepcopy(self.playbook_context)
        context['hive_case_id'] = self.cleaned_data['hive_case'] or None
        var_map = dict()
        for step_id, step in context["step_vars"].items():
            for var in step.values():
                var_map[slugify(f"step_var_{step_id}_{var['var_id']}")] = var
        for var in context["workflow_vars"].values():
            var_map[slugify(f"workflow_var_{var['var_id']}")] = var
        
        for key, value in self.cleaned_data.items():
            if key in var_map:
                var_map[key]["var_value"] = value
        return context
    
    def make_var_field(self, prefix, var_dict):
        match var_dict['var_type']:
            case 'string' | 'uuid' | 'mac-addr' | 'ipv4-addr' | 'ipv6-addr' | 'uri' | 'sha256-hash' | 'hexstring':
                field = CustomCharField(
                    label=var_dict['var_id'],
                    initial=var_dict['var_value'],
                )
            case 'integer' | 'long':
                field = forms.IntegerField(
                    label=var_dict['var_id'],
                    initial=var_dict['var_value'],
                )
            case 'dictionary':
                field = CustomJSONField(
                    label=var_dict['var_id'],
                    initial=var_dict['var_value'],
                )
            case _:
                return
        field.required = True
        self.fields[slugify(f"{prefix}_{var_dict['var_id']}")] = field
        return slugify(f"{prefix}_{var_dict['var_id']}")
