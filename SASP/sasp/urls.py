from django.urls import path,include
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import routers

import sasp.views as views
import sasp.views.admin as admin_views
import sasp.views.playbook_views as playbook_views
# import sasp.views.kafka_views as kafka_views
import sasp.views.hive_views as hive_views
import sasp.views.base as base_views
from .auth.keycloak_integration import keycloak_login_landing_page, keycloak_logout

router = routers.DefaultRouter()
router.register(r'playbook', base_views.PlaybookViewSet,basename='api-playbook')
router.register(r'playbook_object/(?P<pb_id>[^/.]+)', base_views.Playbook_ObjectViewSet,basename='api-playbook_object')
router.register(r'semantic_relation', base_views.Semantic_RelationViewSet,basename='api-semantic_relation')
router.register(r'json_export', base_views.Json_ExportViewSet,basename='api-json_export')
# router.register("sync_forms", FormSync_View, basename="api-sync_forms")

def redirect_to_index(request):
    return redirect('index')

urlpatterns = [
    path('', base_views.IndexView.as_view(), name='index'),

    path('accounts/', admin_views.UserProfileDetailView.as_view(), name='settings'),
    path('accounts/connected-tools/<str:login_name>', admin_views.UserProfileLoginView.as_view(), name='settings-logins'),
    # path('accounts/login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', keycloak_logout, name='logout'),

    path('accounts/sso_landing/', keycloak_login_landing_page, name='keycloak-login-landing-page'),

    path('playbook/view/<int:pk>', playbook_views.PlaybookView.as_view(), name='playbook-detail'),
    path('playbook/edit/<int:pk>', playbook_views.PlaybookObjectEditView.as_view(is_playbook=True), name='playbook-edit'),
    path('playbook/bpmn/<int:pk>', playbook_views.PlaybookBPMNView.as_view(), name='playbook-bpmn'),
    path('playbook/delete/<int:pk>', playbook_views.DeleteView.as_view(type_="playbook"), name='playbook-delete'),
    path('playbook/archive/<int:pk>', playbook_views.ArchiveCreationView.as_view(), name='playbook-archive'),
    path('playbook/new/<str:form>', playbook_views.PlaybookObjectEditView.as_view(is_playbook=True, is_new=True), name='playbook-create'),
    
    path('playbook_object/<int:pk_pb>/view/<int:pk>', playbook_views.PlaybookObjectView.as_view(), name='playbook_object-detail'),
    path('playbook_object/<int:pk_pb>/edit/<int:pk>', playbook_views.PlaybookObjectEditView.as_view(), name='playbook_object-edit'),
    path('playbook_object/<int:pk_pb>/delete/<int:pk>', playbook_views.DeleteView.as_view(type_="playbook_object"), name='playbook_object-delete'),
    path('playbook_object/<int:pk_pb>/new/<str:form>', playbook_views.PlaybookObjectEditView.as_view(is_new=True), name='playbook_object-create'),
        
    path('sharing/json/validator', base_views.JsonValidatorView.as_view(), name='sharing-json-validator') ,
    path('sharing/json/import/cacao-1-1', views.sharing_views.SharingCACAO1_1.ImportJsonView.as_view(), name='sharing-import-json-cacao-1-1'),
    path('sharing/json/export/cacao-1-1', views.sharing_views.SharingCACAO1_1.ExportJsonView.as_view(), name='sharing-export-json-cacao-1-1'),
    path('sharing/misp/import/cacao-1-1', views.sharing_views.SharingCACAO1_1.ImportMispView.as_view(), name='sharing-import-misp-cacao-1-1'),
    path('sharing/misp/export/cacao-1-1', views.sharing_views.SharingCACAO1_1.ExportMispView.as_view(), name='sharing-export-misp-cacao-1-1'),
    path('sharing/kafka/import/cacao-1-1', views.sharing_views.SharingCACAO1_1.ImportKafkaView.as_view(), name='sharing-import-kafka-cacao-1-1'),
    path('sharing/kafka/export/cacao-1-1', views.sharing_views.SharingCACAO1_1.ExportKafkaView.as_view(), name='sharing-export-kafka-cacao-1-1'),

    path('api/', include(router.urls)),
    path('api/command', base_views.test_api, name='api-command'),

    path('hive/', hive_views.TheHiveDashboard, name='thehive-dashboard'),
    path('hive/action/run/<str:playbook_id>/<str:case_id>', hive_views.TheHiveRunPlaybook, name='thehive-run-playbook'), 
    path('hive/action/delete/<int:pk>', hive_views.deleteTheHiveRun, name='thehive-delete-run'),
    path('hive/details/<int:pk>', hive_views.TheHiveRunDetails.as_view(), name='thehive-run-details'),
    path('hive/confirm_request/<int:pk>/<str:uuid>/<str:action>', hive_views.confirm_request, name='thehive-confirm-request'),

    # Redirects
    path('accounts/login/', redirect_to_index),
    
]
# Only register these if DEBUG is True
if settings.DEBUG:
    urlpatterns += [
        path('debug/', views.DEBUGView.as_view(), name='debug'),
    ]