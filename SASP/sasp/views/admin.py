from typing import Any
from sasp.models.auth import UserProfile

import sasp.views as views

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
            print("DEBUG","UserProfileLoginView: get_context_data",self.request.user.get_username())
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
        
        context['login_info'] = obj
        return context
