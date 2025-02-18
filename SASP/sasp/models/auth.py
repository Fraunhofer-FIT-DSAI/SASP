from django.db import models
from django.contrib.auth.models import User, AnonymousUser, Group, Permission

from .app_settings import AppSettings


class UserProfile(models.Model):
    """Our wrapper around the User model"""

    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    sso_token = models.JSONField(null=True, blank=True)
    sso_token_expires = models.DateTimeField(null=True, blank=True)
    sso_user_info = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return f"{self.user.username} ({self.display_name})"
    
    def __repr__(self):
        return f"UserProfile({self.user.username})"
    
    def get_unique_id(self, extended=False):
        org_id = AppSettings.get_key('application_id')
        if self.sso_user_info:
            name = self.sso_user_info.get('email') or self.sso_user_info.get('preferred_username')
            if extended:
                return name + '|' + self.sso_user_info.get('sub') + '@' + org_id, True
            else:
                return name + '|' + self.sso_user_info.get('sub') + '@' + org_id
        if extended:
            return self.user.username + '@' + org_id, False
        else:
            return self.user.username + '@' + org_id
    
    def get_display_id(self):
        org_id = AppSettings.get_key('application_id')
        if self.sso_user_info:
            name = self.sso_user_info.get('email') or self.sso_user_info.get('preferred_username')
            return name
        if self.display_name:
            return self.display_name
        return self.user.username
    

class LoginInfo(models.Model):
    """Holds connection information for Hive, Misp etc. so it can be user specific"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='logins')


    name = models.CharField(max_length=255)

    # Human readable label for the login, defaults to the name of the login
    label = models.CharField(max_length=255, null=True, blank=True)

    url = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    cert = models.JSONField(null=True, blank=True)
    token = models.CharField(max_length=255, null=True, blank=True)
    expires = models.DateTimeField(null=True, blank=True)
    additional_fields = models.JSONField(null=True, blank=True)
    connected = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.user.username} - {self.label}"
    
    def __repr__(self):
        return f"LoginInfo({self.user.user.username} - {self.label})"