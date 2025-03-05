from django import forms
from django.utils.translation import gettext as _

# from sasp.external_apis.hive_cortex_api import Hive
from sasp.models.auth import LoginInfo

import sasp.wiki_interface as wiki_interface
import sasp.MISPInterface as MISPInterface
import sasp.external_apis.hive_cortex_api as hive_cortex_api

class LoginInfoForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.model:'LoginInfo' = kwargs.pop("model")
        super().__init__(*args, **kwargs)

class SMWLoginInfoForm(LoginInfoForm):
    url = forms.CharField(
        label=_("URL"), 
        help_text=_("URL of the Semantic MediaWiki instance")
    )
    username = forms.CharField(
        label=_("Username"), 
        help_text=_("Username for the Semantic MediaWiki instance")
    )
    password = forms.CharField(
        label=_("Password"), 
        help_text=_("Password for the Semantic MediaWiki instance"), 
        widget=forms.PasswordInput(render_value=True)
    )
    user_path = forms.CharField(
        label=_("User Path"), 
        help_text=_("Path to the wiki pages e.g. '/index.php/'")
    )
    script_path = forms.CharField(
        label=_("Script Path"), 
        help_text=_("Path to the wiki scripts e.g. '/w/'")
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].initial = self.fields['url'].initial or self.model.url
        self.fields['username'].initial = self.fields['username'].initial or self.model.username
        self.fields['password'].initial = self.fields['password'].initial or self.model.password
        self.fields['user_path'].initial = self.fields['user_path'].initial or self.model.additional_fields.get('user_path', '')
        self.fields['script_path'].initial = self.fields['script_path'].initial or self.model.additional_fields.get('script_path', '')
    
    def save(self):
        self.model.url = self.cleaned_data['url']
        self.model.username = self.cleaned_data['username']
        self.model.password = self.cleaned_data['password']
        self.model.additional_fields = {
            'user_path': self.cleaned_data['user_path'],
            'script_path': self.cleaned_data['script_path']
        }
        self.model.connected = wiki_interface.Wiki.connect(
            self.model.url, 
            self.model.additional_fields['script_path'], 
            self.model.username, 
            self.model.password
        )
        self.model.save()

class MISPLoginInfoForm(LoginInfoForm):
    url = forms.CharField(label=_("URL"), help_text=_("URL of the MISP instance"))
    api_key = forms.CharField(
        label=_("API Key"), 
        help_text=_("API key for the MISP instance"), 
        widget=forms.PasswordInput(render_value=True)
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].initial = self.fields['url'].initial or self.model.url
        self.fields['api_key'].initial = self.fields['api_key'].initial or self.model.token
    
    def save(self):
        self.model.url = self.cleaned_data['url']
        self.model.token = self.cleaned_data['api_key']
        self.model.save()
        try:
            MISPInterface.MISPInterface(self.model.user.user.username)
            self.model.connected = True
        except Exception as e:
            self.model.connected = False
        self.model.save()

class HiveLoginInfoForm(LoginInfoForm):
    url = forms.CharField(label=_("URL"), help_text=_("URL of the Hive instance"))
    api_key = forms.CharField(
        label=_("API Key"), 
        help_text=_("API key for the Hive instance"), 
        widget=forms.PasswordInput(render_value=True)
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].initial = self.fields['url'].initial or self.model.url
        self.fields['api_key'].initial = self.fields['api_key'].initial or self.model.token
    
    def save(self):
        self.model.url = self.cleaned_data['url']
        self.model.token = self.cleaned_data['api_key']
        self.model.save()
        
        hive, _ = hive_cortex_api.Hive.update_user(self.model.user.user)
        self.model.connected = hive
        
        self.model.save()

class CortexLoginInfoForm(LoginInfoForm):
    url = forms.CharField(label=_("URL"), help_text=_("URL of the Cortex instance"))
    api_key = forms.CharField(
        label=_("API Key"), 
        help_text=_("API key for the Cortex instance"), 
        widget=forms.PasswordInput(render_value=True)
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].initial = self.fields['url'].initial or self.model.url
        self.fields['api_key'].initial = self.fields['api_key'].initial or self.model.token
    
    def save(self):
        self.model.url = self.cleaned_data['url']
        self.model.token = self.cleaned_data['api_key']
        self.model.save()
        
        _, cortex = hive_cortex_api.Hive.update_user(self.model.user.user)
        self.model.connected = cortex
        
        self.model.save()