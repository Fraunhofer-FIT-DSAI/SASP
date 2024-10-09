from django.core.management.base import BaseCommand
from sasp.models import Playbook, Playbook_Object

class Command(BaseCommand):
    def handle(self, *args, **options):
        Playbook.objects.all().delete()
        Playbook_Object.objects.all().delete()