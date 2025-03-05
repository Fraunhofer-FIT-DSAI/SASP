from typing import Any
from sasp.models.auth import UserProfile, LoginInfo

from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib import messages
from django.http import HttpResponseRedirect

import sasp.views as views
import sasp.forms.admin as forms

import sasp.wiki_interface as wiki_interface
import sasp.MISPInterface as MISPInterface
import sasp.external_apis.hive_cortex_api as hive_cortex_api

import json

class UserProfileDetailView(views.SASPBaseView):
    template_name = 'settings.html'
    help_text = "Overview of the current user's settings"


    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['errors'] = []
        context['active'] = 'Overview'
        if self.request.user.get_username() != '':
            try:
                user = self.request.user.profile
            except UserProfile.DoesNotExist:
                context['errors'].append(f'User profile not found for user {self.request.user.get_username()}')
                return context
        else:
            user = UserProfile.objects.get(user__username='default')
        
        self.object = user
        context['active_user'] = user
        context['user_attributes'] = dict()
        if 'email' in user.sso_user_info:
            context['user_attributes']['Email'] = user.sso_user_info['email']
        if 'email_verified' in user.sso_user_info:
            context['user_attributes']['Email Verified'] = user.sso_user_info['email_verified']
        if 'preferred_username' in user.sso_user_info:
            context['user_attributes']['Username'] = user.sso_user_info['preferred_username']
        if 'given_name' in user.sso_user_info:
            context['user_attributes']['First Name'] = user.sso_user_info['given_name']
        if 'family_name' in user.sso_user_info:
            context['user_attributes']['Last Name'] = user.sso_user_info['family_name']
        if 'sub' in user.sso_user_info:
            context['user_attributes']['ID'] = user.sso_user_info['sub']
        
        if len(context['user_attributes']) == 0:
            context['user_attributes'] = {'No user attributes found': 'No user attributes found'}
        return context

class UserProfileLoginView(views.SASPBaseView):
    template_name = 'settings_login_overview.html'
    help_text = "Overview of the current user's connected tools"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['errors'] = []

        if self.request.user.get_username() != '':
            try:
                user = self.request.user.profile
            except UserProfile.DoesNotExist:
                context['errors'].append(f'User profile not found for user {self.request.user.get_username()}')
                return context
        else:
            user = UserProfile.objects.get(user__username='default')
            
        # Get string parameter from url
        login_name = self.kwargs.get('login_name', None)
        login_info = user.logins.filter(name=login_name).first()
        context['active'] = login_info.name
        context['active_user'] = user

        obj = dict()
        obj['Name'] = login_info.name
        obj['Label'] = login_info.label
        if login_info.url:
            obj['Connection URL'] = login_info.url
        if login_info.username:
            obj['Username'] = login_info.username
        if login_info.password:
            obfuscated = login_info.password
            if len(obfuscated) > 9:
                obfuscated = '*' * (len(obfuscated) - 3) + obfuscated[-3:]
            else:
                obfuscated = '*' * len(obfuscated)
            obj['Password'] = obfuscated
        if login_info.token:
            obfuscated = login_info.token
            if len(obfuscated) > 9:
                obfuscated = '*' * (len(obfuscated) - 3) + obfuscated[-3:]
            else:
                obfuscated = '*' * len(obfuscated)
            obj['Token'] = obfuscated
        if login_info.expires:
            obj['Expires'] = login_info.expires
        if login_info.cert:
            obj['Certificate'] = json.dumps(login_info.cert, indent=4)
        
        context['Connected'] = _("Connected") if login_info.connected else _("Not Connected")
        
        if login_info.name in ['smw','misp','hive']:
            context['edit_url'] = reverse('settings-logins-edit', kwargs={'login_name': login_info.name})
            context['reconnect_url'] = reverse('settings-logins-reconnect', kwargs={'login_name': login_info.name})
        
        context['login_info'] = obj
        return context

class UserProfileLoginReconnectView(views.SASPBaseView):
    def reconnect_smw(self, login_info: 'LoginInfo'):
        login_info.connected = wiki_interface.Wiki.connect(
            login_info.url, 
            login_info.additional_fields['script_path'], 
            login_info.username, 
            login_info.password
        )
        login_info.save()
    
    def reconnect_misp(self, login_info: 'LoginInfo'):
        try:
            MISPInterface.MISPInterface(login_info.user.user.username)
            login_info.connected = True
        except Exception as _:
            login_info.connected = False
        login_info.save()
    
    def reconnect_hive(self, login_info: 'LoginInfo'):
        hive = hive_cortex_api.Hive.update_user(login_info.user.user)
        login_info.connected = hive
        login_info.save()
    
    def get(self, request, *args, **kwargs):
        login_name = self.kwargs.get('login_name', None)
        
        if self.request.user.get_username() != '':
            try:
                user = self.request.user.profile
            except UserProfile.DoesNotExist:
                return self.error_response(f'User profile not found for user {self.request.user.get_username()}')
        else:
            user = UserProfile.objects.get(user__username='default')
        
        login_info = user.logins.filter(name=login_name).first()
        if login_info.name == 'smw':
            self.reconnect_smw(login_info)
        elif login_info.name == 'misp':
            self.reconnect_misp(login_info)
        elif login_info.name == 'hive':
            self.reconnect_hive(login_info)
        else:
            return self.error_response(f'Login type {login_info.name} not implemented')
        
        if login_info.connected:
            return self.success_response(f'{login_info.name} successfully reconnected')
        else:
            return self.success_response(f'{login_info.name} could not be reconnected')
    
    def error_response(self, message):
        messages.error(self.request, message)
        return HttpResponseRedirect(reverse('settings-logins', kwargs={'login_name': self.kwargs.get('login_name', None)})
        )
    
    def success_response(self, message):
        messages.success(self.request, message)
        return HttpResponseRedirect(reverse('settings-logins', kwargs={'login_name': self.kwargs.get('login_name', None)})
        )

class UserProfileLoginEditView(views.SASPBaseFormView):
    template_name = 'settings_login_edit.html'
    help_text = "Overview of the current user's connected tools"
    
    
    def get_form_class(self):
        """Return the form class to use."""
        login_name = self.kwargs.get('login_name', None)
        login_info = self.request.user.profile.logins.filter(name=login_name).first()
        if login_info.name == 'smw':
            return forms.SMWLoginInfoForm
        elif login_info.name == 'misp':
            return forms.MISPLoginInfoForm
        elif login_info.name == 'hive':
            return forms.HiveLoginInfoForm
        else:
            raise NotImplementedError(f'Login type {login_info.name} not implemented')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        login_name = self.kwargs.get('login_name', None)
        login_info = self.request.user.profile.logins.filter(name=login_name).first()
        kwargs['model'] = login_info
        return kwargs
    
    def get_success_url(self):
        return reverse('settings-logins', kwargs={'login_name': self.kwargs.get('login_name', None)})

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['errors'] = []

        if self.request.user.get_username() != '':
            try:
                user = self.request.user.profile
            except UserProfile.DoesNotExist:
                context['errors'].append(f'User profile not found for user {self.request.user.get_username()}')
                return context
        else:
            user = UserProfile.objects.get(user__username='default')
            
        # Get string parameter from url
        login_name = self.kwargs.get('login_name', None)
        login_info = user.logins.filter(name=login_name).first()
        context['active'] = login_info.name
        context['active_user'] = user

        obj = dict()
        obj['Connected'] = login_info.connected
        obj['Name'] = login_info.name
        obj['Label'] = login_info.label
        
        context['login_info'] = obj
        return context