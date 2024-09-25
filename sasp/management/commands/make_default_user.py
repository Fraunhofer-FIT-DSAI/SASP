from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
from sasp.models.auth import UserProfile, LoginInfo
from sasp.models.app_settings import AppSettings
from dotenv import dotenv_values

from pathlib import Path

class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='default')
        except User.DoesNotExist:
            user = User.objects.create_user('default', email=None, password='default')
        
        # Default user should have all permissions
        permissions = Permission.objects.all()
        for permission in permissions:
            user.user_permissions.add(permission)
        user.save()
        
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = UserProfile(user=user)
            profile.save()
        
        # Login Infos
        # /dockersmw/tools/wiki-tool/sasp/management/commands/make_default_user.py
        path = Path(__file__).parent / '..' / '..' / '..' / 'config'
        path = path.resolve()
        config = dotenv_values(path / 'config.env')
        keys = dotenv_values(path / 'keys.env')
        
        # Semantic Mediawiki
        # self.site = Site(getenv("URL_BASE"), scheme=getenv("PROTOCOL"),
        #                 path=getenv("API_PATH"))
        # self.site.login(getenv("SYS_USERNAME"), getenv("BOT_PASSWORD"))
        try:
            login_info = LoginInfo.objects.get(user=profile, name='smw')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='smw')
        
        login_info.label = 'Semantic Mediawiki'
        login_info.name = 'smw'
        
        required_fields = ['PROTOCOL', 'URL_BASE', 'SYS_USERNAME', 'BOT_PASSWORD', 'API_PATH', 'USER_PATH']
        if not config or not all(field in config for field in required_fields):
            print('Config is missing required fields, using defaults')
            login_info.url = 'http://localhost:8081'
            login_info.username = 'WikiSysop'
            login_info.password = 'a@rkct3k9aqhhc1fhtq5j1vsql8kp5ec94'
            login_info.additional_fields = {
                'script_path': '/w/',
                'user_path': '/wiki/'
            }
        else:
            login_info.url = config['PROTOCOL'] + '://' + config['URL_BASE']
            login_info.username = config['SYS_USERNAME']
            login_info.password = config['BOT_PASSWORD']
            login_info.additional_fields = {
                'script_path': config['API_PATH'],
                'user_path': config['USER_PATH']
            }
        login_info.save()

        # MISP
        try:
            login_info = LoginInfo.objects.get(user=profile, name='misp')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='misp')
        
        login_info.label = 'MISP'
        login_info.name = 'misp'

        if not config or 'MISP_URL' not in config or not keys or 'MISP_KEY' not in keys:
            print('No MISP configuration found')
            login_info.url = ''
            login_info.token = ''
        else:
            login_info.url = config['MISP_URL']
            login_info.token = keys['MISP_KEY']
        login_info.save()

        # Hive
        try:
            login_info = LoginInfo.objects.get(user=profile, name='hive')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='hive')
        
        login_info.label = 'TheHive'
        login_info.name = 'hive'
        
        if not config or 'HIVE_URL' not in config or not keys or 'HIVE_API_KEY' not in keys:
            print('No Hive configuration found')
            login_info.url = ''
            login_info.token = ''
        else:
            login_info.url = config['HIVE_URL']
            login_info.token = keys['HIVE_API_KEY']
        login_info.save()

        # Cortex
        try:
            login_info = LoginInfo.objects.get(user=profile, name='cortex')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='cortex')
        
        login_info.label = 'Cortex'
        login_info.name = 'cortex'

        if not config or 'CORTEX_URL' not in config or not keys or 'CORTEX_API_KEY' not in keys:
            print('No Cortex configuration found')
            login_info.url = ''
            login_info.token = ''
        else:
            login_info.url = config['CORTEX_URL']
            login_info.token = keys['CORTEX_API_KEY']
        login_info.save()

        # Keycloak
        try:
            login_info = LoginInfo.objects.get(user=profile, name='keycloak')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='keycloak')

        login_info.label = 'Keycloak'
        login_info.name = 'keycloak'

        if (not config or 
            'KEYCLOAK_URL' not in config or 
            not keys or 'KEYCLOAK_CLIENT_ID' not in config or 
            'KEYCLOAK_CLIENT_SECRET' not in keys or
            'KEYCLOAK_REALM' not in config
            ):
            print('No Keycloak configuration found')
            login_info.url = ''
            login_info.username = ''
            login_info.token = ''
            additional_fields = {}
        else:
            login_info.url = config['KEYCLOAK_URL']
            login_info.username = config['KEYCLOAK_CLIENT_ID']
            login_info.token = keys['KEYCLOAK_CLIENT_SECRET']
            additional_fields = {
                'realm': config.get('KEYCLOAK_REALM', 'master')
            }
        login_info.additional_fields = additional_fields
        login_info.save()

        # Kafka
        try:
            login_info = LoginInfo.objects.get(user=profile, name='kafka')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='kafka')

        login_info.label = 'Kafka'
        login_info.name = 'kafka'

        if (not config or
            'KAFKA_CLIENT_ID' not in config or
            'KAFKA_BOOTSTRAP_SERVERS' not in config or
            'KAFKA_SSL_CA_LOCATION' not in config or
            'KAFKA_SSL_CERTIFICATE_LOCATION' not in config or
            'KAFKA_SSL_KEY_LOCATION' not in config or
            'KAFKA_CONSUMER_GROUP_ID' not in config or
            'KAFKA_REGISTRY_PLAIN_SSL_KEY_LOCATION' not in config or
            'KAFKA_REGISTRY_URL' not in config or
            not keys or
            'KAFKA_SSL_KEY_PWD' not in keys
            ):
            print('No Kafka configuration found')
            login_info.additional_fields = {
                'client.id': '',
                'bootstrap_servers': '',
                'registry.url': '',
                'ssl.ca.location': '',
                'ssl.certificate.location': '',
                'ssl.key.location': '',
                'group.id': '',
                'registry.plain.ssl.key.location': '',
                'ssl.key.password': ''
            }
        else:
            login_info.additional_fields = {
                'client.id': config['KAFKA_CLIENT_ID'],
                'bootstrap_servers': config['KAFKA_BOOTSTRAP_SERVERS'],
                'registry.url': config['KAFKA_REGISTRY_URL'],
                'ssl.ca.location': config['KAFKA_SSL_CA_LOCATION'],
                'ssl.certificate.location': config['KAFKA_SSL_CERTIFICATE_LOCATION'],
                'ssl.key.location': config['KAFKA_SSL_KEY_LOCATION'],
                'group.id': config['KAFKA_CONSUMER_GROUP_ID'],
                'registry.plain.ssl.key.location': config['KAFKA_REGISTRY_PLAIN_SSL_KEY_LOCATION'],
                'ssl.key.password': keys['KAFKA_SSL_KEY_PWD']
            }
        
        for key in ['ssl.ca.location', 'ssl.certificate.location', 'ssl.key.location', 'registry.plain.ssl.key.location']:
            path = Path(login_info.additional_fields[key]).resolve()
            if not path.exists():
                print(f'Path for "{key}" does not exist')
                print(f'Path resolved to: {path}')
            else:
                login_info.additional_fields[key] = str(path)


        login_info.save()

        # AppSettings
        if config:
            for key,value in config.items():
                if key.startswith('APP_'):
                    AppSettings.set_key(key[4:], value)
                    print(f'Setting {key[4:]} to {value}')

        print('Default user created')
