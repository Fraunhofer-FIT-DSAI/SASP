from django.db import models

from datetime import datetime, date
import json

class AppSettingsManager(models.Manager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.defaults = {
            'application_id': ("FRAUNHOFER-SASP",'str')
        }
        # For getting from db
        self.typecast = {
            'str': str,
            'int': int,
            'bool': lambda x: x=="True",
            'date': date.fromisoformat,
            'datetime': datetime.fromisoformat,
            'json': json.loads,
        }

        # For saving to db
        self.typecast_rev = {
            'str': lambda x: x,
            'int': str,
            'bool': str,
            'date': lambda x: x.isoformat(),
            'datetime': lambda x: x.isoformat(),
            'json': json.dumps,
        }

        self.infer_type = {
            str: 'str',
            int: 'int',
            bool: 'bool',
            date: 'date',
            datetime: 'datetime',
            list: 'json',
            dict: 'json',
        }
        
        # Typecast the defaults
        self.defaults = {
            key: (self.typecast_rev[value[1]](value[0]), value[1]) for key, value in self.defaults.items()
        }
    
    def get_queryset(self) -> models.QuerySet:
        prev_set_objects = super().get_queryset()

        added_keys = False
        for key, value in self.defaults.items():
            if not prev_set_objects.filter(key=key).exists():
                AppSettings.objects.create(
                    key=key, 
                    value=value[0], 
                    value_type=value[1], 
                    profile='default'
                )
                added_keys = True
        if added_keys:
            prev_set_objects = super().get_queryset()
        return prev_set_objects
    
    def get(self, key, profile='default'):
        try:
            setting = AppSettings.objects.get(key=key, profile=profile)
            return self.typecast[setting.value_type](setting.value)
        except AppSettings.DoesNotExist:
            setting =  AppSettings.objects.create(
                key=key, 
                value=self.defaults[key][0], 
                value_type=self.defaults[key][1], 
                profile=profile
            )
            return self.typecast[setting.value_type](setting.value)
        
    def set(self, key, value, value_type=None, profile='default'):
        if value_type is None:
            if type(value) not in self.infer_type:
                raise ValueError(f'Could not infer value_type from value: {value}')
            value_type = self.infer_type[type(value)]

        if value_type not in self.typecast:
            raise ValueError(f'Invalid value_type: {value_type}')
        
        # clear key
        AppSettings.objects.filter(key=key, profile=profile).delete()

        # typecast value
        value = self.typecast_rev[value_type](value)
        # set key
        AppSettings.objects.create(
            key=key,
            value=value,
            value_type=value_type,
            profile=profile
        ).save()

class AppSettings(models.Model):
    key = models.CharField(max_length=200, unique=True)
    value = models.TextField()
    value_type = models.CharField(max_length=200, default='str', choices=(
        ('str','String'),
        ('int','Integer'),
        ('bool','Boolean'),
        ('date','Date'),
        ('datetime','DateTime'),
        ('json','JSON'),
    ))

    # Not used yet, but if then the combination of key and profile should be unique
    profile = models.CharField(max_length=200, default='default')

    objects = models.Manager()
    c_objects = AppSettingsManager()

    def get_key(key, profile='default'):
        return AppSettings.c_objects.get(key=key, profile=profile)
    
    def set_key(key, value, value_type=None, profile='default'):
        AppSettings.c_objects.set(key, value, value_type, profile)


    def __str__(self):
        return self.key
    
    def display_value(self):
        return self.value[:50]
    display_value.short_description = 'Value'

    class Meta:
        verbose_name = "App Setting"
        verbose_name_plural = "App Settings"
