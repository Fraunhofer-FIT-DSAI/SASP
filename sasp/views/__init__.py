from typing import Any
from django.views import generic
from django.urls import reverse
from django.utils.translation import gettext as _
from ..auth.keycloak_integration import KeycloakLoginRequiredMixin

import sasp.knowledge as knowledge

import logging


logger = logging.getLogger(__name__)


class DEBUGView(generic.TemplateView):
    template_name = "debug.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["debug"] = True
        context["full_tag"] = '<p class="text-danger">This is a test</p>'
        return context


class SASPCommonView:
    """Common view for SASP views"""

    def get_context_data(self, **kwargs):
        # If "help_text" is defined in object
        context = dict()
        if hasattr(self, "help_text"):
            context = {"help_text": self.help_text}

        context["modals"] = dict()

        context["locations"] = {
            "basic": {
                "import": {
                    "locations": [
                        {"href": reverse(value["Import"][0][1]), "label": _(key)}
                        for key, value in knowledge.Sharing.supported.items()
                        if "Import" in value
                    ],
                    "label": _("Import"),
                },
                "export": {
                    "locations": [
                        {"href": reverse(value["Export"][0][1]), "label": _(key)}
                        for key, value in knowledge.Sharing.supported.items()
                        if "Export" in value
                    ],
                    "label": _("Export"),
                },
                "tools": {
                    "locations": [
                        {
                            "href": reverse("sharing-json-validator"),
                            "label": _("CACAO v2 - Validator"),
                        }
                    ],
                    "label": _("Tools"),
                },
                "uncategorized": [
                    {
                        "href": reverse("thehive-dashboard"), 
                        "label": _("TheHive"),
                        "disabled": True,
                    }
                ],
            }
        }
        return context


class SASPBaseView(generic.TemplateView, SASPCommonView):
    """Base view for SASP views (unused so far because I didn't think of it until now)"""

    # https://docs.djangoproject.com/en/4.2/ref/class-based-views/base/#templateview
    def __init__(self, **kwargs: Any) -> None:
        KeycloakLoginRequiredMixin.__init__(self)
        generic.TemplateView.__init__(self, **kwargs)
        SASPCommonView.__init__(self)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(SASPCommonView.get_context_data(self, **kwargs))
        return context


class SASPBaseDetailView(generic.DetailView, SASPCommonView):
    """Base detail view for SASP views (unused so far because I didn't think of it until now)"""

    # https://docs.djangoproject.com/en/4.2/ref/class-based-views/generic-display/#detailview
    def __init__(self, **kwargs: Any) -> None:
        KeycloakLoginRequiredMixin.__init__(self, **kwargs)
        generic.DetailView.__init__(self, **kwargs)
        SASPCommonView.__init__(self, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(SASPCommonView.get_context_data(self, **kwargs))
        return context


class SASPBaseFormView(generic.edit.FormView, SASPCommonView):
    """Base form view for SASP views (unused so far because I didn't think of it until now)"""

    # https://docs.djangoproject.com/en/4.2/ref/class-based-views/generic-editing/#formview
    def __init__(self, **kwargs: Any) -> None:
        KeycloakLoginRequiredMixin.__init__(self, **kwargs)
        generic.edit.FormView.__init__(self, **kwargs)
        SASPCommonView.__init__(self, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(SASPCommonView.get_context_data(self, **kwargs))
        return context


import sasp.views.admin as admin_views
import sasp.views.base as base_views
import sasp.views.hive_views as hive_views
import sasp.views.playbook_views as playbook_views
import sasp.views.sharing as sharing_views
