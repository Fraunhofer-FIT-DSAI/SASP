from typing import Any, Dict
from django.urls import reverse
from django.shortcuts import render
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.contrib import messages
from django.utils.translation import gettext as _

import sasp.views as views
import sasp.forms as forms
from ..auth.keycloak_integration import KeycloakLoginRequiredMixin
from ..models import (
    Playbook,
    Playbook_Object,
    Semantic_Relation
)
from sasp.knowledge import KnowledgeBase as kb

from collections import OrderedDict

import json
import urllib.parse
import logging

class TopbarMixin:
    def get_context_topbar(self):
        context = {}
        context["wiki_url"] = kb.wiki_url_pattern.format(
            page_name=self.object.wiki_page_name
        ).replace(" ", "_")
        buttons_basic = OrderedDict()
        buttons_basic['dropdown-new'] = {
            "type_": "dropdown",
            "tag": "topbar-dropdown-new",
            "disabled": "disabled" if self.object.archived else '',
            "header": {
                "text": _("New"),
            },
            "links": [
                {
                    "text": pbo_form.get_cls_label(),
                    "href": reverse("playbook_object-create", args=[self.playbook.pk, pbo_form.slug]),
                }
                for pbo_form in self.playbook.playbook_object_class.get_new_forms()
            ],
        }
        buttons_extended = OrderedDict()
        buttons_extended['button-edit'] = {
            "type_": "button",
            "text": "Edit",
            "href": self.object.get_edit_url(),
            "disabled": "disabled" if self.object.archived else '',
        }
        buttons_extended['button-delete'] = {
            "type_": "button",
            "text": "Delete",
            "outline": "danger",
            "href": self.object.get_delete_url(),
        }
        context["buttons"] = {
            "basic": buttons_basic,
            "extended": buttons_extended,
        }
        return {'topbar': context}

class SidebarMixin:
    @staticmethod
    def get_context_sidebar(obj, playbook_objects):
        sidebar = {}
        for obj_ in playbook_objects:
            header = obj_.get_cls_label()
            name = obj_.get_label()
            url = obj_.get_absolute_url()
            priority = obj_.get_priority()
            active = obj_.pk == obj.pk if obj else False
            sidebar[header] = sidebar.get(header, []) + [(name, url, active, priority)]
        # Sort sidebar by priority group by header
        sidebar_list = []
        header_priority = {header: max(x[3] for x in items) for header, items in sidebar.items()}
        header_priority = sorted(header_priority.items(), key=lambda x: x[1], reverse=True)        
        for header, __ in header_priority:
            items = sorted(sidebar[header], key=lambda x: x[3], reverse=True)
            sidebar_list.append((header, 'collapse show' if any(x[2] for x in items) else 'collapse', items))
        return sidebar_list
    
class PlaybookObjectView(KeycloakLoginRequiredMixin,views.SASPBaseDetailView,TopbarMixin,SidebarMixin):
    model = Playbook_Object
    template_name = "playbook_object.html"
    logger = logging.getLogger(__name__)
    
        
    def get_context_buttons(self, object):
        context = {}
        quick_links = {
            "individual": [],
            "grouped": dict(),
        }
        
        if object.archived:
            return context
        
        for header,label,obj_form,field in object.get_new_objects():
            href = reverse("playbook_object-create", 
                           kwargs={
                               "pk_pb": object.playbook.pk,
                                 "form": obj_form,
                               }
                           )
            params = urllib.parse.urlencode({
                "parent_field": field,
                "parent_object": object.pk,
            })
            href += f"?{params}"
            
            if header is None:
                quick_links["individual"].append({
                    "label": label,
                    "href": href,
                })
            else:
                if header not in quick_links["grouped"]:
                    quick_links["grouped"][header] = []
                quick_links["grouped"][header].append({
                    "label": label,
                    "href": href,
                })
        if quick_links["individual"] or quick_links["grouped"]:
            context["quick_links"] = quick_links
        return context
    def get_context_object_data(self, object):
        context = {
            "object_data": {
                "fields": object.get_fields_context(),
            }
        }
        return context
    def get_context_semantic_refs(self, refs):
        refs = [
            {
                "display_name": obj.get_name(),
                "href": obj.get_absolute_url(),
                "priority": obj.get_priority(),
            }
           for obj in (ref.subject_field.resolve_subclass() for ref in refs)
        ]
        refs = sorted(refs, key=lambda x: x["priority"], reverse=True)
        # Clean up duplicates
        refs_clean = []
        refs_clean_href = set()
        for ref in refs:
            if ref["href"] not in refs_clean_href:
                refs_clean.append(ref)
                refs_clean_href.add(ref["href"])
        refs = refs_clean
        return refs
    
    def get_context_basics(self):
        context = {}
        context["scripts"] = {
            "json_viewer": True,
        }
        context["delete_url"] = self.object.get_delete_url()
        context["name"] = self.object.get_label()
        context["wiki_name"] = self.object.wiki_page_name
        return context

    def get_context_warnings(self):
        try:
            for warning in self.object.get_context_warnings():
                messages.warning(self.request, warning)
        except Exception as e:
            self.logger.error(f"Error while getting warnings for playbook object {self.object.pk}: {e}")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self.object.resolve_subclass()
        self.playbook = self.object.playbook.resolve_subclass()
        playbook_objects = [obj.resolve_subclass() for obj in self.object.playbook.playbook_objects.all()]
        refs = Semantic_Relation.objects.filter(
            playbook=self.object.playbook, object_field=self.object
        )
        
        context.update(self.get_context_basics())
        context["sidebar"] = self.get_context_sidebar(self.object, playbook_objects=playbook_objects)
        context.update(self.get_context_topbar())
        context.update(self.get_context_buttons(self.object))
        context.update(self.get_context_object_data(self.object))

        context["semantic_refs"] = self.get_context_semantic_refs(refs=refs)
        self.get_context_warnings()

        return context

class PlaybookView(PlaybookObjectView, TopbarMixin):
    model = Playbook
    template_name = "playbook_view.html"
    help_text = kb.help_texts.playbook.page__OBJ()
    
    def get_context_topbar(self):
        context = super(PlaybookObjectView,self).get_context_topbar().get('topbar')
        context["bpmn_url"] = reverse("playbook-bpmn", args=[self.playbook.pk])
        context["buttons"]["basic"]['dropdown-new']['links'] = [
                {
                    "text": pbo_form.get_cls_label(),
                    "href": reverse("playbook_object-create", args=[self.playbook.pk, pbo_form.slug]),
                }
                for pbo_form in self.playbook.playbook_object_class.get_new_forms()
            ]
        context["buttons"]["extended"]['button-edit']['href'] = self.playbook.get_edit_url()
        context["buttons"]["extended"]['button-delete']['href'] = self.playbook.get_delete_url()
        context["buttons"]["extended"]['button-archive'] = {
            "type_": "modal_button",
            "text": "Archive",
            "disabled": 'disabled' if self.playbook.archived else '',
            "modal": {
                "id": "modal-archive-form",
            },
        }
        return {'topbar': context}
    
    def get_context_data(self, **kwargs):
        self.playbook = self.object.resolve_subclass()
        self.object = self.playbook.get_root()
        context = super().get_context_data(**kwargs)
        context['modals']['modal_archive_form'] = {
            "title": _("Archive Playbook: %(name)s" % {"name": self.playbook.get_label()}),
            "id": "modal-archive-form",
            "form": forms.base.ArchiveCreateForm(self.request.POST or None, initial={"playbook" : self.playbook}),
        }
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        if "submit-archive-form" in request.POST:
            form = context['modals']['modal_archive_form']['form']
            if form.is_valid():
                try:
                    archive_tag:str = form.cleaned_data["archive_tag"]
                    playbook = form.cleaned_data["playbook"]
                    archived = Playbook.make_archive(playbook, archive_tag)
                except Exception as e:
                    messages.error(request, f"Error while archiving playbook: {e}")
                    return self.render_to_response(context)
                messages.success(request, f"Playbook {playbook.get_label()} archived as {archived.get_label()}.")
                return HttpResponseRedirect(reverse("playbook-detail", args=[archived.pk]))
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Error in field {field}: {error}")
        return self.render_to_response(context)

class DeleteView(KeycloakLoginRequiredMixin, views.SASPBaseView):
    object_ = None
    type_ = None
    help_text = "Please confirm that you want to delete this object."
    
    def __init__(self, **kwargs: Any) -> None:
        self.type_ = kwargs.pop("type_", None)
        super().__init__(**kwargs)
    
    def init_vars(self):
        pk = self.kwargs.get("pk")
        if not pk:
            messages.error(self.request, "No id provided.")
            return False
        if self.type_ == "playbook":
            try:
                self.object_ = Playbook.objects.get(pk=pk)
                self.object_ = self.object_.resolve_subclass()
            except Playbook.DoesNotExist:
                messages.error(self.request, f"Playbook with id {pk} does not exist.")
                return False
        elif self.type_ == "playbook_object":
            playbook = self.kwargs.get("pk_pb")
            if not playbook:
                messages.error(self.request, "No playbook id provided.")
                return False
            try:
                self.object_ = Playbook_Object.objects.get(pk=pk, playbook=playbook)
                self.object_ = self.object_.resolve_subclass()
            except Playbook_Object.DoesNotExist:
                messages.error(self.request, f"Playbook object with id {pk} does not exist.")
                return False
        else:
            messages.error(self.request, f"Invalid type {self.type_}.")
            return False
        return True
    
    def dispatch(self, request, *args, **kwargs):
        if not self.init_vars():
            return HttpResponseRedirect(reverse("index"))
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        if self.type_ == "playbook":
            if "confirm" in self.request.GET:
                return self.delete_playbook()
            else:
                return self.confirm_playbook()
        elif self.type_ == "playbook_object":
            if "confirm" in self.request.GET:
                return self.delete_playbook_object()
            else:
                return self.confirm_playbook_object()
        else:
            return HttpResponseRedirect(reverse("index"))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Delete: ") + self.object_.get_name()
        return context
    
    def confirm_playbook(self):
        context = self.get_context_data()
        playbook_objects = [obj.resolve_subclass() for obj in self.object_.playbook_objects.all()]
        context["sidebar"] = PlaybookView.get_context_sidebar(
            obj=None, 
            playbook_objects=playbook_objects
        )
        context["name_deleted_object"] = self.object_.get_label()
        context["list_derived_objects"] = [obj.get_label() for obj in playbook_objects]
        context["confirm_url"] = reverse("playbook-delete", kwargs={"pk": self.object_.pk})+"?confirm"
        return render(self.request, "delete_confirm.html", context)
    
    def confirm_playbook_object(self):
        context = self.get_context_data()
        playbook_objects = [obj.resolve_subclass() for obj in self.object_.playbook.playbook_objects.all()]
        context["sidebar"] = PlaybookView.get_context_sidebar(
            obj=self.object_, 
            playbook_objects=playbook_objects
        )
        context["name_deleted_object"] = self.object_.get_name()
        context["list_derived_objects"] = []
        context["confirm_url"] = reverse("playbook_object-delete", kwargs={"pk": self.object_.pk, "pk_pb": self.object_.playbook.pk})+"?confirm"
        return render(self.request, "delete_confirm.html", context)
    
    def delete_playbook(self):
        self.object_.remove()
        return HttpResponseRedirect(reverse("index"))
    def delete_playbook_object(self):
        self.object_.remove()
        return HttpResponseRedirect(reverse("playbook-detail", kwargs={"pk": self.object_.playbook.pk}))

class PlaybookBPMNView(KeycloakLoginRequiredMixin, views.SASPBaseDetailView, SidebarMixin):
    model = Playbook
    template_name = "playbook_bpmn.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        playbook = self.object.resolve_subclass() # Loads type specific object if available (e.g. CACAO_1_1)
        context["playbook_objects"] = [obj.resolve_subclass() for obj in playbook.playbook_objects.all()]
        context["wiki_url"] = kb.wiki_url_pattern.format(
            page_name=self.object.wiki_page_name
        ).replace(" ", "_")
        context["help_text"] = kb.help_texts.bpmn.page__OBJ()
        context["name"] = playbook.get_name()
        context["bpmn"],error_list = playbook.bpmn()
        for error in error_list:
            messages.error(self.request, error)
        
        context["href_dict"] = {obj.wiki_page_name: reverse("playbook_object-detail", kwargs={"pk": obj.pk, "pk_pb": obj.playbook.pk}) for obj in context["playbook_objects"]}
        context["href_dict"] = json.dumps(context["href_dict"])

        # Generate headers for sidebar
        context["sidebar"] = self.get_context_sidebar(self.object, playbook_objects=context["playbook_objects"])

        return context

class PlaybookObjectEditView(KeycloakLoginRequiredMixin, views.SASPBaseFormView):
    help_text = """In this view you can edit or create a playbook object."""
    template_name = "playbook_object_edit.html"
    error_url = "index"
    playbook = None
    playbook_cls = None
    object = None
    object_cls = None
    
    parent_object = None
    parent_field = None
    
    # Control signals set by urls.py
    is_new = None
    is_playbook = None
    # Control signals set by setup
    parameter_error = False
    
    def __init__(self, *args, is_new=False, is_playbook=False, **kwargs):
        self.is_new = is_new
        self.is_playbook = is_playbook
        super().__init__(*args, **kwargs)
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        
        if self.is_new:
            if not kwargs.get("form"):
                messages.error(self.request, "No form provided.")
                self.parameter_error = True
                return
            
            # Check if form exists and get object class
            try:
                self.object_cls = Playbook_Object.get_proxyclass(kwargs.get("form"), slug=True)
            except KeyError:
                messages.error(self.request, f"Playbook object form '{kwargs.get('form')}' does not exist.")
                self.parameter_error = True
                return
            
            if self.is_playbook:
                # If we are making a new playbook, we need to get the playbook class
                try:
                    self.playbook_cls = Playbook.get_proxyclass(kwargs.get("form"), slug=True)
                except KeyError:
                    messages.error(self.request, f"Playbook form '{kwargs.get('form')}' does not exist.")
                    self.parameter_error = True
                    return
                # And create the playbook object
                self.playbook = self.playbook_cls()
            else:
                # If we are making a new playbook object, we need to get the playbook from parameters
                try:
                    self.playbook = Playbook.objects.get(pk=kwargs.get("pk_pb"))
                except Playbook.DoesNotExist:
                    messages.error(self.request, f"Playbook with id '{kwargs.get('pk_pb')}' does not exist.")
                    self.parameter_error = True
                    return
                if self.playbook.archived:
                    messages.error(self.request, f"Playbook with id '{kwargs.get('pk_pb')}' is archived and no new objects can be created.")
                    self.parameter_error = True
                    return
                self.playbook = self.playbook.resolve_subclass()
            # And create the playbook object
            self.object = self.object_cls(playbook=self.playbook)
        else:
            # We are editing an existing playbook object
            if self.is_playbook:
                # We are editing a root playbook object
                try:
                    self.playbook = Playbook.objects.get(pk=kwargs.get("pk"))
                except Playbook.DoesNotExist:
                    messages.error(self.request, f"Playbook with id '{kwargs.get('pk')}' does not exist.")
                    self.parameter_error = True
                    return
                if self.playbook.archived:
                    messages.error(self.request, f"Playbook with id '{kwargs.get('pk')}' is archived and can't be edited.")
                    self.parameter_error = True
                    return
                self.playbook = self.playbook.resolve_subclass()
                self.object = self.playbook.get_root()
            else:
                # We are editing a playbook object
                try:
                    self.object = Playbook_Object.objects.get(pk=kwargs.get("pk"))
                except Playbook_Object.DoesNotExist:
                    messages.error(self.request, f"Playbook object with id '{kwargs.get('pk')}' does not exist.")
                    self.parameter_error = True
                    return
                if self.object.archived:
                    messages.error(self.request, f"Playbook object with id '{kwargs.get('pk')}' is archived and can't be edited.")
                    self.parameter_error = True
                    return
                self.object = self.object.resolve_subclass()
                self.playbook = self.object.playbook.resolve_subclass()
        
        if self.is_new and not self.is_playbook and self.request.GET.get("parent_object") and self.request.GET.get("parent_field"):
            try:
                self.parent_object = Playbook_Object.objects.get(pk=self.request.GET.get("parent_object"))
            except Playbook_Object.DoesNotExist:
                messages.error(self.request, f"Parent playbook object with id {self.request.GET.get('parent_object')} does not exist.")
                self.parameter_error = True
                return
            self.parent_object = self.parent_object.resolve_subclass()
            self.parent_field = self.request.GET.get("parent_field")
    
    def dispatch(self, request, *args, **kwargs):
        if self.parameter_error:
            return HttpResponseRedirect(reverse(self.error_url))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.is_new and self.is_playbook:
            playbook_objects = [] # New playbook, no objects yet
        else:
            playbook_objects = [obj.resolve_subclass() for obj in self.playbook.playbook_objects.all()]
            
        context["sidebar"] = PlaybookView.get_context_sidebar(
            obj=self.object, 
            playbook_objects=playbook_objects
        )
        
        new_dropdown = {
            "tag": "topbar-dropdown-new",
            "type_": "dropdown",
            "header": {
                "text": _("New"),
            },
            "links": [],
        }
        if self.is_new and self.is_playbook:
            new_dropdown['links'] = [
                {
                    "text": pb_form.get_cls_label(),
                    "href": reverse("playbook-create", args=[pb_form.slug]),
                }
                for pb_form in Playbook.get_new_forms()
            ]
        else:
            new_dropdown['links'] = [
                {
                    "text": pb_form.get_cls_label(),
                    "href": reverse("playbook_object-create", args=[self.playbook.pk, pb_form.slug]),
                }
                for pb_form in self.object.get_new_forms()
            ]
        
        context["topbar"] = {
            "buttons": {
                "basic": [
                    new_dropdown,
                ],
                "extended": [],
            },
        }
        context["name"] = self.object.get_name() or f"New {self.object.get_label()}"
        return context
    
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)
    
    def get_form_class(self) -> type:
        return self.object.get_form_class()
    
    def get_form_kwargs(self) -> Dict[str, Any]:        
        kwargs = super().get_form_kwargs()
        
        kwargs["object_cls"] = self.object_cls
        kwargs["object"] = self.object
        kwargs["playbook_cls"] = self.playbook_cls
        kwargs["playbook"] = self.playbook
        
        kwargs["is_playbook"] = self.is_playbook
        kwargs["is_new"] = self.is_new
        
        kwargs["parent_object"] = self.parent_object
        kwargs["parent_field"] = self.parent_field
        return kwargs
    
    def form_valid(self, form: Any) -> HttpResponse:
        form.save()
        return HttpResponseRedirect(self.object.get_absolute_url())

class ArchiveCreationView(KeycloakLoginRequiredMixin, views.generic.View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        try:
            playbook = Playbook.objects.get(pk=pk)
            archive_tag:str = request.GET.get("archive_tag", None)
            if not archive_tag:
                messages.error(request, "No archive tag provided.")
                return HttpResponseRedirect(reverse("index"))
            
            archived = Playbook.make_archive(playbook, archive_tag)
        except Playbook.DoesNotExist:
            messages.error(request, f"Playbook with id '{pk}' does not exist.")
            return HttpResponseRedirect(reverse("index"))
        # except Exception as e:
        #     messages.error(request, f"Error while archiving playbook: {e}")
        #     return HttpResponseRedirect(reverse("index"))
        return HttpResponseRedirect(reverse("playbook-detail", args=[archived.pk]))
