from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.http import (
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.utils.translation import gettext as _

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from ..serializers import (
    PlaybookSerializer,
    Playbook_ObjectSerializer,
    Semantic_RelationSerializer,
)
from ..models import (
    Playbook,
    Playbook_Object,
    Semantic_Relation,
)
from ..db_syncs import WikiDBSync
from ..logic_management import LogicManager
from ..wiki_forms import WikiFormManager
from ..util.view_utils import serialize_table
from ..auth.keycloak_integration import keycloak_login_required, KeycloakLoginRequiredMixin
from . import SASPBaseView, logger

import sasp.knowledge as knowledge
import sasp.models.cacao_1_1
import sasp.models.sappan

import json

wiki_db_sync = WikiDBSync()
kb = knowledge.KnowledgeBase()
manager = LogicManager()

# Create your views here.

class IndexView(KeycloakLoginRequiredMixin, SASPBaseView):
    template_name = "index.html"
    help_text = kb.help_texts.index_page__OBJ()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # wiki_db_sync.update_playbooks()
        playbooks = Playbook.query(archived='All')
        context["playbooks"] = playbooks
        context["table_main"] = self.playbook_table(playbooks)
        context["js_context"] = {
            'target_tables' : ['table_main'],
        }
        
        # New Object Dropdown
        context["dropdown_new"] = {
            "tag": "topbar-dropdown-new",
            "header": {
                "text": _("New"),
            },
            "links": [
                {
                    "text": pb_form.get_cls_label(),
                    "href": reverse("playbook-create", args=[pb_form.slug]),
                }
                for pb_form in Playbook.proxyclasses
            ],
        }
        
        return context
    
    def playbook_table(self, playbooks):
        table = dict()
        table["caption"] = "Playbooks"
        table["class"] = ["table", "table-striped", "table-bordered", "table-hover"]
        table["thead"] = dict()
        table["thead"]["columns"] = ["Playbook Name", "Form", "Last Updated", "Archived"]
        table["rows"] = []
        table["id"] = "table_main"
        playbooks = [playbook.resolve_subclass() for playbook in playbooks]
        for playbook in playbooks:
            table["rows"].append(
                {
                    'id': f'row-{playbook.pk}',
                    'cells': [
                        {'content': playbook.get_label(), 'href': reverse('playbook-detail', args=[playbook.pk])},
                        {'content': playbook.get_root_class().get_cls_label()},
                        {'content': playbook.last_change.strftime("%Y-%m-%d %H:%M:%S")},
                        {'content': "Yes" if playbook.archived else "No"},
                    ]
                }
            )
        return serialize_table(table)

class JsonValidatorView(KeycloakLoginRequiredMixin, SASPBaseView):
    help_text = kb.help_texts.sharing.json.validator__OBJ(),
    template_name = "sharing_json_validator.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['labels'] = {
            x.split("__")[0]: kb.labels.common[x]()
            for x in kb.labels.common
            if x.endswith("__TXT")
        }
        context['playbooks'] = []
        context['errors'] = []
        return context

def DummyPage(request, pb_id):
    if isinstance(pb_id, int):
        pb_id = Playbook.objects.get(pk=pb_id).name
        message = f"Exported playbook {pb_id}"
    else:
        message = f"Imported playbook {pb_id}"
    return render(request, "dummy_page.html", context={"message": message})



class PlaybookViewSet(KeycloakLoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows playbooks to be viewed or edited.
    """

    queryset = Playbook.objects.all()
    serializer_class = PlaybookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def retrieve(self, request, pk=None):
        queryset = Playbook.objects.filter(wiki_page_name=pk)
        serializer = PlaybookSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

class Playbook_ObjectViewSet(KeycloakLoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows playbook pages to be viewed or edited.
    """

    queryset = Playbook_Object.objects.all()
    serializer_class = Playbook_ObjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def retrieve(self, request, pb_id=None, pk=None):
        try:
            playbook = Playbook.objects.get(wiki_page_name=pb_id)
        except Playbook.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        queryset = Playbook_Object.objects.filter(playbook=playbook, wiki_page_name=pk)
        serializer = Playbook_ObjectSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class Semantic_RelationViewSet(KeycloakLoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows semantic relations to be viewed or edited.
    """

    queryset = Semantic_Relation.objects.all()
    serializer_class = Semantic_RelationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class Json_ExportViewSet(KeycloakLoginRequiredMixin, viewsets.ViewSet):
    """
    API endpoint that allows playbooks to be exported in JSON format.
    """

    def retrieve(self, request, pk=None):
        try:
            playbook = Playbook.objects.get(wiki_page_name=pk)
        except Playbook.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            json_data = playbook.resolve_subclass().export_to_json()
            response = Response(json_data)
        except Exception:
            response = Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return response

    def list(self, request):
        # Redirect to playbookviewset
        return HttpResponseRedirect(reverse("api-playbook-list"))


# Very simple view to test the API, expects no parameters, executes a method and returns the output as a JSON
@keycloak_login_required
def test_api(request):
    if request.method == "GET":
        # Get action parameter
        action = request.GET.get("action", None)
        # Call the method
        wiki_form_manager = WikiFormManager()
        result = wiki_form_manager.api_call(action=action)
        # Return the result as a JSON
        return JsonResponse(result)
    else:
        # Return an error
        return JsonResponse({"error": "Only GET requests are supported."})


# "archived-playbook-delete", # Delete an archived playbook
# "archived-playbook_object-detail", # View an archived playbook object
# "archived-playbook-detail", # View an archived playbook
# "archived-playbook-import", # Set an archived playbook to active
# "playbook-archive", # archive a playbook

@keycloak_login_required
def archiveArchivePlaybook(request, pk=None):
    if pk is None:
        print("No pk")
        return HttpResponseBadRequest("Bad request")
    pk = get_object_or_404(Playbook, pk=pk)

    # Load the version number from the request body
    try:
        version = json.loads(request.body.decode("utf-8")).get("version", None)
    except json.JSONDecodeError:
        logger.error("Could not decode JSON from request body.")
        version = None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        version = None

    # Print all data from the request

    if version is None:
        print("No version")
        return HttpResponseBadRequest("Bad request")
    manager.archivePlaybook(pk, version)
    return HttpResponseRedirect(reverse("playbook-detail", args=[pk.pk]))