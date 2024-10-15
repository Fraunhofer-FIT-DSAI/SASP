# from django.contrib.auth.decorators import login_required
# from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, logout
from datetime import timedelta
from django.utils import timezone
from functools import wraps
from urllib.parse import urlparse
from django.urls import reverse

from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url
from django.http import HttpResponseRedirect
from django.contrib import messages

from sasp.models.auth import UserProfile, LoginInfo
from keycloak import KeycloakOpenID

# Enables use without a Keycloak instance, but is not recommended
BYPASS_KEYCLOAK = True

def keycloak_openid():
    """Wrapper around the KeycloakOpenID object"""
    try:
        keycloak_config = UserProfile.objects.get(user__username='default').logins.get(name='keycloak')
        keycloak_openid = KeycloakOpenID(
            server_url=keycloak_config.url,
            realm_name=keycloak_config.additional_fields['realm'],
            client_id=keycloak_config.username,
            client_secret_key=keycloak_config.token
        )
    except UserProfile.DoesNotExist:
        raise ValueError('No default user found, have you run make_default_user?')
    except LoginInfo.DoesNotExist:
        raise ValueError('No keycloak login info found for default user, have you run make_default_user?')
    return keycloak_openid

def test_func(user):
    # Should get current user's token and check if it's valid
    # If user is anonymous, check default user
    # TAG:MULTIPLE_USERS, TAG:KEYCLOAK
    if not user.is_authenticated:
        return False
    else:
        user = user.profile
    token = user.sso_token
    if not token:
        return False
    keycloak = keycloak_openid()
    try:
        if timezone.now() > user.sso_token_expires:
            token = keycloak.refresh_token(token['refresh_token'])
            user.sso_token = token
            user.sso_token_expires = timezone.now() + timedelta(seconds=token['expires_in'])
            user.save()
    except Exception:
        return False
    # TODO: Add basic permission check at this point. I.e. user has access to resource SASP, more fine grained
    # permissions if and when we need them should use the django permissions system (probably expanded for keycloak)
    # TAG:KEYCLOAK, TAG:PERMISSIONS
    return True

def keycloak_user_passes_test(
    test_func, login_url=None, redirect_field_name='redirect_uri'
):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if BYPASS_KEYCLOAK:
                if request.user.is_anonymous:
                    user = UserProfile.objects.get(user__username='default')
                    if not request.session.get('keycloak_bypass_warning', False):
                        messages.warning(
                            request, 
                            'Bypassing Keycloak. This enables use without a Keycloak instance, but is not recommended.'
                            )
                        request.session['keycloak_bypass_warning'] = True
                    login(request, user.user)
                return view_func(request, *args, **kwargs)
            elif not test_func(request.user):
                path = request.build_absolute_uri()
                resolved_login_url = resolve_url(login_url or keycloak_openid().auth_url(redirect_uri='', scope='openid profile email') or settings.LOGIN_URL)
                # If the login url is the same scheme and net location then use the
                # path as the "next" url.
                login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
                current_scheme, current_netloc = urlparse(path)[:2]
                if (not login_scheme or login_scheme == current_scheme) and (
                    not login_netloc or login_netloc == current_netloc
                ):
                    path = request.get_full_path()
                
                # TAG:KEYCLOAK
                request.session['redirect_uri'] = str(path)
                path = request.build_absolute_uri(reverse('keycloak-login-landing-page'))
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(
                    path,
                    resolved_login_url,
                    redirect_field_name,
                )
            else:
                return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator

def keycloak_login_required(
        function=None, redirect_field_name='redirect_uri', login_url=None):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = keycloak_user_passes_test(
        test_func,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

class KeycloakLoginRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated."""

    login_url = None
    permission_denied_message = "You don't have permission to access this page."
    raise_exception = False
    redirect_field_name = 'redirect_uri'

    def get_login_url(self) -> str:
        return self.login_url or keycloak_openid().auth_url(redirect_uri='', scope='openid profile email')

    def handle_no_permission(self):
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())

        path = self.request.build_absolute_uri()
        resolved_login_url = resolve_url(self.get_login_url() or settings.LOGIN_URL)
        # If the login url is the same scheme and net location then use the
        # path as the "next" url.
        login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
        current_scheme, current_netloc = urlparse(path)[:2]
        if (not login_scheme or login_scheme == current_scheme) and (
            not login_netloc or login_netloc == current_netloc
        ):
            path = self.request.get_full_path()
        
        # TAG:KEYCLOAK
        self.request.session['redirect_uri'] = str(path)
        path = self.request.build_absolute_uri(reverse('keycloak-login-landing-page'))
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(
            path,
            resolved_login_url,
            self.get_redirect_field_name(),
        )

    def dispatch(self, request, *args, **kwargs):
        if BYPASS_KEYCLOAK:
            if request.user.is_anonymous:
                user = UserProfile.objects.get(user__username='default')
                if not request.session.get('keycloak_bypass_warning', False):
                    messages.warning(
                        request, 
                        'Bypassing Keycloak. This enables use without a Keycloak instance, but is not recommended.'
                        )
                    request.session['keycloak_bypass_warning'] = True
                login(request, user.user)
        elif not test_func(request.user):
            return self.handle_no_permission()
                    
        return super().dispatch(request, *args, **kwargs)
    
    def logged_in(self, request=None) -> bool:
        request = request or self.request
        if BYPASS_KEYCLOAK:
            if request.user.is_anonymous:
                user = UserProfile.objects.get(user__username='default')
                if not request.session.get('keycloak_bypass_warning', False):
                    messages.warning(
                        request, 
                        'Bypassing Keycloak. This was created as a temporary measure while we wait for "https://sso.cyberseas-io.eu/"'
                        'credentials in February 2024. Please do not rely on this for production.'
                        )
                    request.session['keycloak_bypass_warning'] = True
                login(request, user.user)
            return True
        return test_func(request.user)

def keycloak_login_landing_page(request):
    # This is the page we will be redirected to after logging in
    # We will use this to update the user's token and then redirect to the page we were trying to access
    
    real_redirect_uri = request.session.get('redirect_uri', reverse('index'))
    request.session['redirect_uri'] = None

    try:
        code = request.GET.get('code')
        if not code:
            raise ValueError('No code in response')
        keycloak = keycloak_openid()

        redirect_uri = request.build_absolute_uri(reverse('keycloak-login-landing-page'))
        # TAG:MULTIPLE_USERS, TAG:KEYCLOAK
        user = UserProfile.objects.get(user__username='default') #TODO: Support for multiple users and automatic user creation
        token = keycloak.token(code=code, redirect_uri=redirect_uri, grant_type='authorization_code')
        user.sso_user_info = keycloak.userinfo(token['access_token'])
        user.sso_token = token
        user.sso_token_expires = timezone.now() + timedelta(seconds=token['expires_in'])
        user.save()
        login(request, user.user)
    except Exception as e:
        messages.error(request, f"Error logging in: {e}")
        return HttpResponseRedirect(reverse('index'))
    return HttpResponseRedirect(real_redirect_uri)

def keycloak_logout(request):
    user = request.user
    if user.is_anonymous:
        user = UserProfile.objects.get(user__username='default')
    else:
        user = user.profile
    keycloak = keycloak_openid()
    redirect_uri = reverse('settings')

    if BYPASS_KEYCLOAK:
        if request.user.is_anonymous:
            return HttpResponseRedirect(redirect_uri)
        logout(request)
        return HttpResponseRedirect(redirect_uri)

    if not user.sso_token:
        return HttpResponseRedirect(redirect_uri)
    try:
        keycloak.logout(user.sso_token['refresh_token'])
    except Exception as e:
        messages.error(request, f"Error logging out: {e}")        
    user.sso_token = dict()
    user.sso_user_info = dict()
    user.save()
    if not request.user.is_anonymous:
        logout(request)
    return HttpResponseRedirect(redirect_uri)