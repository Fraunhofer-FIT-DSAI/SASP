from django.core.management.base import BaseCommand
from sasp.models import Playbook
from pathlib import Path
import json

class Command(BaseCommand):
    def add_arguments(self, parser):
        # Path to playbook json file
        parser.add_argument('--path', type=str, help='Path to playbook json file', required=True)

    def handle(self, *args, **options):
        if options['path']:
            path = Path(options['path'])
            if path.exists():
                file_ = open(path)
                try:
                    json_data = json.load(file_)
                except json.decoder.JSONDecodeError as e:
                    print('Error: Invalid json file')
                    return
                if not json_data:
                    print('Error: Empty json file')
                    return
                new_playbook = Playbook.new_from_json(json_data)
                file_.close()
            else:
                print('Playbook json file not found')
                print(path.absolute())