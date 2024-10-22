from .models import Playbook, Playbook_Object, Semantic_Relation
from django.urls import reverse
from rest_framework import serializers

class PlaybookSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = Playbook
        fields = ['name','description','last_change','wiki_page_name','content','wiki_form','url']
    def get_url(self,obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(reverse('playbook-detail', kwargs={'pk': obj.pk}))
        else:
            return obj.get_absolute_url()

class Playbook_ObjectSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = Playbook_Object
        fields = ['name','description','last_change','wiki_page_name','playbook','content','wiki_form','url']
    def get_url(self,obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(reverse('playbook_object-detail', kwargs={'pk': obj.pk, 'pk_pb': obj.playbook.pk}))
        else:
            return obj.get_absolute_url()

class Semantic_RelationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Semantic_Relation
        fields = ['subject','object','predicate','playbook']