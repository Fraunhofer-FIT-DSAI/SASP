from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
from pathlib import Path

import configparser

from sasp.models.auth import UserProfile, LoginInfo
from sasp.models.app_settings import AppSettings




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
        config = configparser.ConfigParser()
        config.read(path / 'config.ini')
        config_keys = configparser.ConfigParser()
        config_keys.read(path / 'keys.ini')
        
        try:
            login_info = LoginInfo.objects.get(user=profile, name='smw')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='smw')
        
        login_info.label = 'Semantic Mediawiki'
        login_info.name = 'smw'
        
        required_fields = ['url', 'bot_user', 'api_path', 'user_path']
        if not config or 'Wiki' not in config or not all(field in config['Wiki'] for field in required_fields):
            raise Exception('No Semantic Mediawiki configuration found. Required fields: ' + ', '.join(required_fields))
        elif not config_keys or 'Wiki' not in config_keys or 'bot_password' not in config_keys['Wiki']:
            raise Exception('No Semantic Mediawiki keys found. Required fields: bot_password')
        else:
            login_info.url = config['Wiki']['url']
            login_info.username = config['Wiki']['bot_user']
            login_info.password = config_keys['Wiki']['bot_password']
            login_info.additional_fields = {
                'script_path': config['Wiki']['api_path'],
                'user_path': config['Wiki']['user_path']
            }
        login_info.save()

        # MISP
        try:
            login_info = LoginInfo.objects.get(user=profile, name='misp')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='misp')
        
        login_info.label = 'MISP'
        login_info.name = 'misp'

        if (
            not config or 
            'MISP' not in config or 
            'url' not in config['MISP'] or 
            not config_keys or 
            'MISP' not in config_keys or
            'key' not in config_keys['MISP']
            ):
            print('No MISP configuration found')
            login_info.url = ''
            login_info.token = ''
        else:
            login_info.url = config['MISP']['url']
            login_info.token = config_keys['MISP']['key']
        login_info.save()

        # Keycloak
        try:
            login_info = LoginInfo.objects.get(user=profile, name='keycloak')
        except LoginInfo.DoesNotExist:
            login_info = LoginInfo(user=profile, name='keycloak')

        login_info.label = 'Keycloak'
        login_info.name = 'keycloak'

        if (not config or 
            not config_keys or
            'Keycloak' not in config or
            'Keycloak' not in config_keys or
            'url' not in config['Keycloak'] or 
            'client' not in config['Keycloak'] or 
            'realm' not in config['Keycloak'] or
            'client_secret' not in config_keys['Keycloak']
            ):
            print('No Keycloak configuration found')
            login_info.url = ''
            login_info.username = ''
            login_info.token = ''
            additional_fields = {}
        else:
            login_info.url = config['Keycloak']['url']
            login_info.username = config['Keycloak']['client']
            login_info.token = config_keys['Keycloak']['client_secret']
            additional_fields = {
                'realm': config.get('Keycloak', 'realm', fallback='master')
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
            not config_keys or
            'Kafka' not in config or
            'Kafka' not in config_keys or
            'client' not in config['Kafka'] or
            'bootstrap_server' not in config['Kafka'] or
            'registry_url' not in config['Kafka'] or
            'consumer' not in config['Kafka'] or
            'ssl_ca' not in config['Kafka'] or
            'ssl_certificate' not in config['Kafka'] or
            'ssl_key' not in config['Kafka'] or
            'ssl_registry_key' not in config['Kafka'] or
            'ssl_key_pwd' not in config_keys['Kafka']
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
                'client.id': config['Kafka']['client'],
                'bootstrap_servers': config['Kafka']['bootstrap_server'],
                'registry.url': config['Kafka']['registry_url'],
                'group.id': config['Kafka']['consumer'],
                'ssl.ca.location': config['Kafka']['ssl_ca'],
                'ssl.certificate.location': config['Kafka']['ssl_certificate'],
                'ssl.key.location': config['Kafka']['ssl_key'],
                'registry.plain.ssl.key.location': config['Kafka']['ssl_registry_key'],
                'ssl.key.password': config_keys['Kafka']['ssl_key_pwd']
            }
        
        for key in ['ssl.ca.location', 'ssl.certificate.location', 'ssl.key.location', 'registry.plain.ssl.key.location']:
            path = (Path(__file__).parent / '..' / '..' / '..' / 'config' / login_info.additional_fields[key]).resolve()
            if not path.exists():
                print(f'Path for "{key}" does not exist')
                print(f'Path resolved to: {path}')
            else:
                login_info.additional_fields[key] = str(path)


        login_info.save()

        # AppSettings
        if config and 'SASP' in config:
            for key,value in config['SASP'].items():
                if key.startswith('app_'):
                    AppSettings.set_key(key[4:], value)
                    print(f'Setting {key[4:]} to {value}')

        print('Default user created')
