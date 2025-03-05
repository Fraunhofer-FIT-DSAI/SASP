from django.urls import reverse
from django.http import (
    HttpResponse,
    HttpResponseRedirect
)
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.translation import gettext as _

import sasp.views as views
import sasp.forms.sharing as sharing_forms
import sasp.knowledge as knowledge

from sasp.auth.keycloak_integration import KeycloakLoginRequiredMixin
from sasp.MISPInterface import MISPInterface, PyMISPError
from sasp.sharing_kafka.kafka_methods import KafkaInterface
from sasp.sharing_kafka.kafka_topics import SASPPlaybook


import json


"""
NOTE: Plans for minimizing code duplication:
We have multiple playbook standards and multiple sharing platforms and import/export for each.
Structure:
Define a base view.
Create a class for each platform with a list of supported standards.
Each playbook standard will have a view that inherits from the base view and the platform view.
"""

class MISPApiMixin:
    @property
    def api(self):
        if self._api is None:
            try:
                user = self.request.user if not self.request.user.is_anonymous else User.objects.get(username='default')
                self._api = MISPInterface(user.get_username())
            except PyMISPError as __:
                return None
            except Exception as e:
                messages.error(
                    self.request, 
                    _("An unexpected error occurred while connecting to MISP: %(error)s") % {'error': str(e)}
                )
                return None
        return self._api
    
    def test_connection(self) -> bool:
        return self.api is not None

class KafkaApiMixin:
    @property
    def api(self):
        if self._api is None:
            try:
                self._api = KafkaInterface(self.request.user)
            except Exception as e:
                messages.error(
                    self.request, 
                    _("An unexpected error occurred while connecting to Kafka: %(error)s") % {'error': str(e)}
                )
                return None
        return self._api
    
    def test_connection(self) -> bool:
        return self.api is not None

class SharingViewImport(KeycloakLoginRequiredMixin, views.SASPBaseView):
    help_text = None
    template_name = None
    platform_label = None
    standard_label = None
    form = None
    initial_stage = 'search'
    stage_labels = {
        'search': _("Search"),
        'select': _("Select"),
        'submit': _("Submit")
    }
    _api = None
    @property
    def api(self):
        return None
        if self._api is None:
            self._api = "Init your API here"
        return self._api
    
    def test_connection(self) -> bool:
        """Test the connection to the platform"""
        return True
    
    @property
    def action(self):
        if self.request.method == 'GET':
            return None
        elif self.request.method == 'POST':
            if 'search' in self.request.POST:
                return 'search'
            elif 'select' in self.request.POST:
                return 'select'
            elif 'submit' in self.request.POST:
                return 'submit'
        return None
    
    def search(self) -> HttpResponse:
        """Search for playbooks on the platform"""
        return None
    
    def select(self) -> HttpResponse:
        """Select a playbook to import and display possible import options/warnings"""
        return None
    
    def submit(self) -> HttpResponse:
        """Submit the selected playbook for import"""
        return None
    
    def get(self, request, *args, **kwargs):
        # Dispatch depending on the action
        if self.action is None or not self.test_connection():
            return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if self.action == 'search':
            return self.search()
        if self.action == 'select':
            return self.select()
        if self.action == 'submit':
            return self.submit()
        return super().post(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context["sidebar"] = []
        for platform in knowledge.Sharing.supported:
            collapse = 'collapse' if platform != self.platform_label else 'collapse show'
            items = []
            for action in knowledge.Sharing.supported[platform]:
                for item in knowledge.Sharing.supported[platform][action]:
                    items.append((
                        f"{action}: {item[0]}",
                        reverse(item[1]),
                        self.standard_label == item[0],
                        0
                    ))
            context["sidebar"].append(
                (platform, collapse, items)
            )
            
            context["title"] = f"Import {self.platform_label} - {self.standard_label}"
        
        context['form'] = self.form(stage=self.initial_stage)
        context['stage_labels'] = self.stage_labels
        context['stage'] = self.initial_stage
        
        context["platform_disconnected"] = not self.test_connection()
        context["platform_label"] = self.platform_label
        
        return context
    
    def render_to_response(self, context, **response_kwargs):
        """Render the response with the context and the current template"""
        return super().render_to_response(context, **response_kwargs)

class SharingViewExport(KeycloakLoginRequiredMixin, views.SASPBaseView):
    help_text = None
    template_name = None
    platform_label = None
    standard_label = None
    form = None
    
    _api = None
    @property
    def api(self):
        return None
        if self._api is None:
            self._api = "Init your API here"
        return self._api
    
    def test_connection(self) -> bool:
        """Test the connection to the platform"""
        return True
    
    def export(self, data: dict):
        """Search for playbooks on the platform"""
        return None
    
    def sanitize(self, data: dict, tlp_level: int) -> dict:
        """Sanitize the data before exporting
         - TLP level: 0 = white, 1 = green, 2 = amber, 3 = red
        """
        return data
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["platform_label"] = self.platform_label
        context["standard_label"] = self.standard_label
        
        context["platform_disconnected"] = not self.test_connection()
        
        context["buttons"] = {
            "submit": {
                "label": _("Publish"),
            }
        }
        
        context["sidebar"] = []
        for platform in knowledge.Sharing.supported:
            collapse = 'collapse' if platform != self.platform_label else 'collapse show'
            items = []
            for action in knowledge.Sharing.supported[platform]:
                for item in knowledge.Sharing.supported[platform][action]:
                    items.append((
                        f"{action}: {item[0]}",
                        reverse(item[1]),
                        self.standard_label == item[0],
                        0
                    ))
            context["sidebar"].append(
                (platform, collapse, items)
            )
            
            context["title"] = f"Export {self.platform_label} - {self.standard_label}"
        
        context['form'] = self.form
        return context
        
    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        form = self.form(request.POST)
        response = HttpResponseRedirect(reverse('index'))
        if form.is_valid():
            try:
                response = self.export(form.cleaned_data)
                messages.success(request, _("Playbook successfully exported."))
            except Exception as e:
                messages.error(
                    request, 
                    _("An unexpected error occurred while exporting the playbook: %(error)s") % {'error': str(e)}
                )
                context = self.get_context_data()
                context['form'] = form
                return self.render_to_response(context)
            return response
        else:
            context = self.get_context_data()
            context['form'] = form
            return self.render_to_response(context)
        
    def render_to_response(self, context, **response_kwargs):
        """Render the response with the context and the current template"""
        return super().render_to_response(context, **response_kwargs)

class SharingCACAO1_1:
    class ImportJsonView(SharingViewImport):
        help_text = _("""On this page you can import a playbook in the JSON format.""")
        platform_label = 'JSON'
        standard_label = 'CACAO 1.1'
        form = sharing_forms.SharingCACAO1_1.JSONImportForm
        template_name = 'sharing/import.html'
        initial_stage = 'select'
        
        @property
        def action(self):
            # If we have post request, via the upload button
            if self.request.method == 'POST':
                if 'select' in self.request.POST:
                    return 'select'
                elif 'submit' in self.request.POST:
                    return 'submit'
            return None
        
        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['search_button_disabled'] = True
            context['stage'] = 'select'
            return context
        
        def select(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, self.request.FILES, stage='select')
            
            if form.is_valid():
                playbook_name = form.cleaned_data['playbook'].get('name', '')
                playbook_json = form.cleaned_data['playbook']
                
                # Reinitialize the form with the cleaned data
                form = self.form(
                    initial={
                        'playbook_name': playbook_name,
                        'playbook_json': playbook_json
                        },
                    stage='submit'
                    )
            
                context['form'] = form
                context['stage'] = 'submit'
                return self.render_to_response(context)
            else:
                context['form'] = form
                context['stage'] = 'select'
                return self.render_to_response(context)
        
        def submit(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, self.request.FILES, stage='submit')
            
            if form.is_valid():
                try:
                    form.save()
                    messages.success(self.request, _("Playbook successfully imported."))
                except Exception as e:
                    messages.error(
                        self.request, 
                        _("An unexpected error occurred while importing the playbook: %(error)s") % {'error': str(e)}
                    )
                return HttpResponseRedirect(reverse('index'))
            else:
                context['form'] = form
                context['stage'] = 'submit'
                return self.render_to_response(context)
    
    class ImportMispView(MISPApiMixin, SharingViewImport):
        help_text = _("""On this page you can import a playbook from a MISP event.""")
        platform_label = 'MISP'
        standard_label = 'CACAO 1.1'
        form = sharing_forms.SharingCACAO1_1.MISPImportForm
        template_name = 'sharing/import.html'
        initial_stage = 'search'
        
        def search(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, stage='search')
            if not form.is_valid():
                context['stage'] = 'search'
            else:
                context['stage'] = 'select'
                results = self.api.search(form.cleaned_data['search_field'])
                form = self.form(stage='select', initial=form.cleaned_data)
                choices = []
                for i in range(len(results['Event-ID'])):
                    label = results['ID'][i]
                    if not label or label == 'N/A':
                        label = results['Event-ID'][i]
                    choices.append((results['Event-ID'][i], label))
                form.fields['playbook'].choices = choices
                self.request.session['misp_search_results'] = choices
            context['form'] = form
            return self.render_to_response(context)
        
        def select(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, stage='select')
            form.fields['playbook'].choices = self.request.session['misp_search_results']
            if not form.is_valid():
                context['stage'] = 'select'
            else:
                context['stage'] = 'submit'
                playbook_json = self.api.get_playbook(form.cleaned_data['playbook'])
                playbook_json = json.loads(playbook_json['playbook-file'])
                form = self.form(stage='submit', initial=form.cleaned_data)
                form.fields['playbook'].choices = self.request.session['misp_search_results']
                form.fields['playbook_json'].initial = playbook_json
                playbook_name = playbook_json.get('name', '')
                form.fields['playbook_name'].initial = playbook_name
                
            context['form'] = form
            return self.render_to_response(context)
        
        def submit(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, stage='submit')
            form.fields['playbook'].choices = self.request.session['misp_search_results']
            if not form.is_valid():
                context['stage'] = 'submit'
            else:
                try:
                    form.save()
                    messages.success(self.request, _("Playbook successfully imported."))
                    return HttpResponseRedirect(reverse('index'))
                except Exception as e:
                    messages.error(
                        self.request, 
                        _("An unexpected error occurred while importing the playbook: %(error)s") % {'error': str(e)}
                    )
                    context['stage'] = 'submit'
            context['form'] = form
            return self.render_to_response(context)
    
    class ImportKafkaView(KafkaApiMixin, SharingViewImport):
        help_text = _("""On this page you can import a playbook from a MISP event.""")
        platform_label = 'Kafka'
        standard_label = 'CACAO 1.1'
        form = sharing_forms.SharingCACAO1_1.KafkaImportForm
        template_name = 'sharing/import.html'
        initial_stage = 'search'
        
        def search(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, stage='search')
            if not form.is_valid():
                context['stage'] = 'search'
            else:
                context['stage'] = 'select'
                results = self.api.get_playbooks()
                
                search_terms = form.cleaned_data["search_field"].split()
                if len(search_terms) == 1 and search_terms[0] == "*":
                    results_filtered = [[key,playbook] for key,playbook in results.items()]
                else:
                    results_filtered = []
                    search_terms = [term.casefold() for term in search_terms]
                    for key,playbook in results.items():
                        for term in search_terms:
                            if ( term in playbook['playbook_id'].casefold() or
                                term in playbook['name'].casefold() or
                                term in playbook['description'].casefold() or
                                any(term in label.casefold() for label in playbook['labels']) or
                                term in playbook['standard'].casefold() or
                                term in playbook['published_by'].casefold() or
                                False):
                                results_filtered.append([key,playbook])
                                break
                
                
                form = self.form(stage='select', initial=form.cleaned_data)
                choices = []
                for key,playbook in results_filtered:
                    label = playbook['name'] or playbook['playbook_id'] or 'N/A'
                    choices.append((key, label))
                form.fields['playbook'].choices = choices
                self.request.session['kafka_search_results'] = choices
            context['form'] = form
            return self.render_to_response(context)
        
        def select(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, stage='select')
            form.fields['playbook'].choices = self.request.session['kafka_search_results']
            if not form.is_valid():
                context['stage'] = 'select'
            else:
                context['stage'] = 'submit'
                playbook_json = self.api.get_playbook(form.cleaned_data['playbook'])
                playbook_json = json.loads(playbook_json['playbook_json'])
                form = self.form(stage='submit', initial=form.cleaned_data)
                form.fields['playbook'].choices = self.request.session['kafka_search_results']
                form.fields['playbook_json'].initial = playbook_json
                playbook_name = playbook_json.get('name', '')
                form.fields['playbook_name'].initial = playbook_name
                
            context['form'] = form
            return self.render_to_response(context)
        
        def submit(self) -> HttpResponse:
            context = self.get_context_data()
            form = self.form(self.request.POST, stage='submit')
            form.fields['playbook'].choices = self.request.session['kafka_search_results']
            if not form.is_valid():
                context['stage'] = 'submit'
            else:
                try:
                    form.save()
                    messages.success(self.request, _("Playbook successfully imported."))
                    return HttpResponseRedirect(reverse('index'))
                except Exception as e:
                    messages.error(
                        self.request, 
                        _("An unexpected error occurred while importing the playbook: %(error)s") % {'error': str(e)}
                    )
                    context['stage'] = 'submit'
            context['form'] = form
            return self.render_to_response(context)
    
    class ExportJsonView(SharingViewExport):
        help_text = _("""On this page you can export a playbook in the JSON format.""")
        platform_label = 'JSON'
        standard_label = 'CACAO 1.1'
        form = sharing_forms.SharingCACAO1_1.JSONExportForm
        template_name = 'sharing/export.html'
        
        def export(self, data: dict):
            playbook = data['playbook'].resolve_subclass()
            # tlp_level = None # Not supported by CACAO 1.1
            file_name = playbook.get_name() + ".json"
            
            playbook_data = playbook.serialize()
            playbook_json = json.dumps(playbook_data, indent=4)
            
            return HttpResponse(
                playbook_json,
                content_type='application/json',
                headers={'Content-Disposition': f'attachment; filename="{file_name}"'}
            )
    
    class ExportMispView(MISPApiMixin, SharingViewExport):
        help_text = _("""On this page you can export a playbook to a MISP event.""")
        platform_label = 'MISP'
        standard_label = 'CACAO 1.1'
        form = sharing_forms.SharingCACAO1_1.MISPExportForm
        template_name = 'sharing/export.html'
        
        def export(self, data: dict):
            playbook = data['playbook'].resolve_subclass()
            playbook_data = playbook.serialize()
            playbook_json = json.dumps(playbook_data, indent=4)
            
            self.api.send_playbook_cacao(playbook_json, playbook.get_name())
            return HttpResponseRedirect(reverse('index'))
    
    class ExportKafkaView(KafkaApiMixin, SharingViewExport):
        help_text = _("""On this page you can export a playbook to a Kafka topic.""")
        platform_label = 'Kafka'
        standard_label = 'CACAO 1.1'
        form = sharing_forms.SharingCACAO1_1.KafkaExportForm
        template_name = 'sharing/export.html'
        
        def export(self, data: dict):
            from sasp.models.cacao_1_1 import CACAO_1_1, CACAO_1_1_Playbook
            playbook:CACAO_1_1 = data['playbook'].resolve_subclass()
            playbook_obj:CACAO_1_1_Playbook = playbook.get_root()
            try:
                playbook_internal_id = playbook_obj.Field_ID.get_field(playbook_obj)
                playbook_name = playbook.get_name()
            except Exception:
                raise ValueError('ID and Name are required fields for sharing a playbook via Kafka.')
            playbook_description = playbook_obj.Field_Description.get_field(playbook_obj, default='No description') #Optional
            playbook_labels = playbook_obj.Field_Labels.get_field(playbook_obj, default=[]) #Optional
            playbook_version = "0" # Cacao versioning uses 'revoked' flag and an entire new playbook for versioning
            playbook_standard = CACAO_1_1.cls_label
            published_by = self.request.user.profile.get_unique_id() #Required

            playbook_json = playbook.serialize()
            playbook_json = json.dumps(playbook_json, indent=2)

            sasp_playbook = SASPPlaybook(
                playbook_id=playbook_internal_id,
                name=playbook_name,
                description=playbook_description,
                labels=playbook_labels,
                version=playbook_version,
                standard=playbook_standard,
                published_by=published_by,
                playbook_json=playbook_json
            )
            
            self.api.produce_playbook(sasp_playbook)
            
            return HttpResponseRedirect(reverse('index'))
    # TODO: Misp, Kafka