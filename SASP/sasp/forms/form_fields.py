from typing import Any
from django import forms
from django.template.defaultfilters import filesizeformat
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from datetime import timezone

class FormFieldMixin:
    def add_classes(self, classes: list):
        classes = set(classes + self.widget.attrs.get('class', '').split())
        self.widget.attrs.update({'class': ' '.join(classes)})
    def add_class(self, class_: str):
        self.add_classes([class_])
    def remove_classes(self, classes: list):
        classes = set(self.widget.attrs.get('class', '').split()) - set(classes)
        self.widget.attrs.update({'class': ' '.join(classes)})
    def remove_class(self, class_: str):
        self.remove_classes([class_])
    def set_placeholder(self, placeholder: str):
        self.widget.attrs.update({'placeholder': placeholder})

class CustomBooleanField(forms.BooleanField, FormFieldMixin):
    pass
class CustomCharField(forms.CharField, FormFieldMixin):
    pass
class CustomChoiceField(forms.ChoiceField, FormFieldMixin):
    pass
class CustomDateField(forms.DateField, FormFieldMixin):
    pass
class CustomDateTimeField(forms.DateTimeField, FormFieldMixin):
    pass
class CustomTimestampField(CustomDateTimeField):
    def to_python(self, value):
        datetm = super().to_python(value)
        if datetm:
            datetm = datetm.astimezone(timezone.utc).replace(tzinfo=None)
            return datetm.isoformat(timespec='seconds') + 'Z'
        return None
        
class CustomDecimalField(forms.DecimalField, FormFieldMixin):
    pass
class CustomDurationField(forms.DurationField, FormFieldMixin):
    pass
class CustomEmailField(forms.EmailField, FormFieldMixin):
    pass
class CustomFileField(forms.FileField, FormFieldMixin):
    """
    Same as FileField, but you can specify:
        * content_types - list containing allowed content_types. Example: ['application/pdf', 'image/jpeg']
        * max_upload_size - a number indicating the maximum file size allowed for upload.
            2.5MB - 2621440
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 5242880
            100MB 104857600
            250MB - 214958080
            500MB - 429916160
    """
    def __init__(self, *args, **kwargs):
        self.content_types = kwargs.pop("content_types", None)
        self.max_upload_size = kwargs.pop("max_upload_size", None)

        super(CustomFileField, self).__init__(*args, **kwargs)
        
        if self.content_types:
            self.widget.attrs.update({'accept': ', '.join(self.content_types)})

    def clean(self, *args, **kwargs):        
        data = super(CustomFileField, self).clean(*args, **kwargs)
        
        try:
            file = data.file
            content_type = file.content_type
            if self.content_types and content_type not in self.content_types:
                raise forms.ValidationError(_('Filetype not supported.'))
            if self.max_upload_size and file._size > self.max_upload_size:
                raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (filesizeformat(self.max_upload_size), filesizeformat(file._size)))
        except AttributeError:
            pass
            
        return data
class CustomFilePathField(forms.FilePathField, FormFieldMixin):
    pass
class CustomFloatField(forms.FloatField, FormFieldMixin):
    pass
class CustomIntegerField(forms.IntegerField, FormFieldMixin):
    pass
class CustomJSONField(forms.JSONField, FormFieldMixin):
    pass
class CustomMultipleChoiceField(forms.MultipleChoiceField, FormFieldMixin):
    pass
class CustomTypedChoiceField(forms.TypedChoiceField, FormFieldMixin):
    pass
class CustomTypedListField(forms.CharField, FormFieldMixin):
    def __init__(self, *args, coerce=lambda val: val, **kwargs):
        self.coerce = coerce
        kwargs['empty_value'] = kwargs.get('empty_value', [])
        super().__init__(*args, **kwargs)
        
    def to_python(self, value: Any | None) -> Any | None:
        values = [x.strip() for x in value.split(',')] if value else []
        return self._coerce(values)
    
    def prepare_value(self, value: Any) -> Any:
        if value is None:
            return ''
        return ", ".join(str(val) for val in value)
    
    def _coerce(self, value):
        if value == self.empty_value or value in self.empty_values:
            return self.empty_value
        new_value = []
        for choice in value:
            try:
                new_value.append(self.coerce(choice))
            except (ValueError, TypeError, ValidationError):
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": choice},
                )
        return new_value
class CustomTokenListField(CustomTypedListField):
    def __init__(self, *args, **kwargs):
        self.token_seperator = kwargs.pop('token_seperator', ',')
        self.choices_only = kwargs.pop('choices_only', False) # If True, only allow choices in the list
        self.choices = kwargs.pop('choices', [])
        super().__init__(*args, **kwargs)
        
        # TODO: Add the javascript to the widget to allow tokenizing the input
    
    def validate(self, value: Any) -> None:
        super().validate(value)
        if self.choices_only:
            for val in value:
                if val not in self.choices:
                    raise ValidationError('Invalid choice: %s' % val)

class Select2TokenListField(forms.MultipleChoiceField, FormFieldMixin):
    def __init__(self, *args, 
                 choices_only=False,
                 **kwargs):
        self.choices_only = choices_only
        super().__init__(*args, **kwargs)
        self.add_class('select2-tags')
    
    _initial = None
    @property
    def initial(self):
        return self._initial
    
    @initial.setter
    def initial(self, value):
        # This is a hack, because the Django widget goes through the choices property
        # when rendering the form field. So if we are setting the initial value and it's
        # not in the choices, we need to add it so that it gets rendered properly.
        
        # Problems:
        #  - Whenever we set initial, we modify the choices property, so the original choices
        #    are indistinguishable from the ones we added.
        #  - Initial only provides the values, not the labels, so we can't add the label to the choices.
        
        if self.choices_only:
            self._initial = value
            return
        
        if value is None:
            self._initial = None
            return
        if not isinstance(value, (list, tuple)):
            raise ValueError('Initial value must be a list or tuple')
        self._initial = value
        for val in value:
            if not self.choices or val not in (x[0] for x in self.choices):
                self.choices = list(self.choices) + [(val, val)]
    
    def to_python(self, value: Any | None) -> Any | None:
        return super().to_python(value)
    
    def prepare_value(self, value: Any) -> Any:
        return super().prepare_value(value)
    
    def valid_value(self, value):
        if self.choices_only:
            return super().valid_value(value)
        else:
            return True

class Select2SingleTokenField(forms.ChoiceField, FormFieldMixin):
    def __init__(self, *args, 
                 choices_only=False,
                 **kwargs):
        self.choices_only = choices_only
        kwargs['required'] = kwargs.get('required', False)
        super().__init__(*args, **kwargs)
        self.add_class('select2-tag')
        if not self.required:
            self.choices = [('', '---------')] + self.choices
            # if not self.initial:
            #     self.initial = ''
    
    _initial = None
    @property
    def initial(self):
        return self._initial
    
    @initial.setter
    def initial(self, value):
        # This is a hack, because the Django widget goes through the choices property
        # when rendering the form field. So if we are setting the initial value and it's
        # not in the choices, we need to add it so that it gets rendered properly.
        
        # Problems:
        #  - Whenever we set initial, we modify the choices property, so the original choices
        #    are indistinguishable from the ones we added.
        #  - Initial only provides the values, not the labels, so we can't add the label to the choices.
        
        if value is None:
            self._initial = ''
            return
        
        if self.choices_only:
            self._initial = value
            return
        
        self._initial = value
        
        if not self.choices or value not in (x for x,y in self.choices):
            self.choices.append((value,value))
    
    def to_python(self, value: Any | None) -> Any | None:
        return super().to_python(value)
    
    def prepare_value(self, value: Any) -> Any:
        return super().prepare_value(value)
    
    def valid_value(self, value):
        if self.choices_only:
            return super().valid_value(value)
        else:
            return True

class CustomFeaturesField(Select2TokenListField):
    def to_python(self, value: Any) -> Any:
        selected = super().to_python(value)
        return {
            key: True for key in selected
        }
    
    def validate(self, value: Any) -> None:
        return super().validate(
            list(value.keys())
        )

class CustomModelChoiceField(forms.ModelChoiceField, FormFieldMixin):
    pass