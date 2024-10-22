from django.core.management.base import BaseCommand
from sasp.models import Playbook, Playbook_Object
from sasp.wiki_forms import WikiFormManager

class Command(BaseCommand):
    def handle(self, *args, **options):
        WikiFormManager.update_wiki()