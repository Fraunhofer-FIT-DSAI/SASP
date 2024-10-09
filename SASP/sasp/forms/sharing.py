from django import forms
from django.utils.translation import gettext as _

from .form_fields import (
    CustomCharField, 
    CustomJSONField, 
    CustomFileField, 
    CustomModelChoiceField,
    CustomChoiceField
)
from sasp.models import Playbook

import json

class ExportForm(forms.Form):
    playbook = CustomModelChoiceField(
        label=_("Playbook"),
        help_text=_("Select a playbook to export"),
        queryset=None
    )
    sanitization = CustomChoiceField(
        label=_("Sanitization"),
        help_text=_("Select the sanitization level for the exported playbook, anything above the selected level will be removed. RED means no sanitization."),
        choices=[
            (0, _("TLP:WHITE")),
            (1, _("TLP:GREEN")),
            (2, _("TLP:AMBER")),
            (3, _("TLP:RED")),
        ],
        initial=3
    )
    
    def __init__(self, *args, **kwargs):
        self.filter = kwargs.pop('filter', {})
        super().__init__(*args, **kwargs)
        self.fields['playbook'].set_placeholder(_("Name of the playbook to export"))

class ImportForm(forms.Form):
    search_field = CustomCharField(
        label=_("Search"),
        required=False,
    )
    playbook = CustomChoiceField(
        label=_("Playbook"),
        choices=[],
        required=False,
        widget=forms.widgets.RadioSelect
    )
    playbook_name = CustomCharField(
        label=_("Playbook Name"),
        help_text=_("Name of the playbook"),
        required=False
    )
    playbook_json = CustomJSONField(
        label=_("Playbook JSON"),
        help_text=_("JSON representation of the playbook"),
        required=False,
        initial={}
    )
    
    
    def __init__(self, *args, stage=None, **kwargs):
        self.stage = stage
        super().__init__(*args, **kwargs)
                
        if stage == 'search':
            allowed_fields = ['search_field']
        elif stage == 'select':
            allowed_fields = ['search_field', 'playbook']
        elif stage == 'submit':
            allowed_fields = ['search_field', 'playbook', 'playbook_name', 'playbook_json']
        else:
            raise ValueError(f"Invalid stage: {stage}")
        self.fields = {key: self.fields[key] for key in allowed_fields}
    
    
    def clean_search_field(self):
        value = self.cleaned_data['search_field']
        if self.stage == 'search' and value in self.fields['search_field'].empty_values:
            self.add_error('search_field', _('This field is required'))
        return value
    
    def clean_playbook(self):
        value = self.cleaned_data['playbook']
        if self.stage == 'select' and value is None:
            self.add_error('playbook', _('This field is required'))
        return value
    
    def clean_playbook_name(self):
        value = self.cleaned_data['playbook_name']
        if self.stage == 'submit' and value in self.fields['playbook_name'].empty_values:
            self.add_error('playbook_name', _('This field is required'))
        return value
    
    def clean_playbook_json(self):
        value = self.cleaned_data['playbook_json']
        if self.stage == 'submit' and value in self.fields['playbook_json'].empty_values:
            self.add_error('playbook_json', _('This field is required'))
        return value

class SharingCACAO1_1:
    class ImportMixin:
        def clean(self):
            cleaned_data = super().clean()
            
            from sasp.models.cacao_1_1 import CACAO_1_1, CACAO_1_1_PlaybookObject
            if 'playbook_json' in cleaned_data and not self.fields['playbook_json'].disabled:
                data = self.cleaned_data['playbook_json']
                deserializer = CACAO_1_1.Deserializer(data)
                try:
                    deserializer.deserialize(name=self.cleaned_data['playbook_name'])
                except CACAO_1_1.Deserializer.DeserializationDuplicateError as e:
                    self.add_error('playbook_name', str(e))
                    return cleaned_data
                except CACAO_1_1.Deserializer.DeserializerMissingNameException as e:
                    self.add_error('playbook_name', str(e))
                    return cleaned_data
                except CACAO_1_1.Deserializer.DeserializationException as e:
                    self.add_error('playbook_json', str(e))
                    return cleaned_data
                except CACAO_1_1_PlaybookObject.Object_Field.Exception_Field_Validation as e:
                    self.add_error('playbook_json', str(e))
                    return cleaned_data
                except Exception as e:
                    self.add_error('playbook_json', str(e))
                    return cleaned_data
            return cleaned_data
        
        def save(self):
            if 'playbook_json' not in self.cleaned_data:
                raise ValueError("Form must be in submit stage to save")
            if 'playbook_name' not in self.cleaned_data:
                raise ValueError("Form must be in submit stage to save")
            if not self.is_valid():
                raise ValueError("Form must be valid to save")
            
            from sasp.models.cacao_1_1 import CACAO_1_1
            data = self.cleaned_data['playbook_json']
            deserializer = CACAO_1_1.Deserializer(data)
            deserializer.deserialize(name=self.cleaned_data['playbook_name'])
            deserializer.save()
    
    class JSONImportForm(ImportMixin, ImportForm):
        playbook = CustomFileField(
            label=_("Playbook"), 
            help_text=_("Select a playbook file to import"),
            content_types=['application/json'],
            max_upload_size=2621440,
            required=False,
        )
        def __init__(self, *args, stage=None, **kwargs):
            super().__init__(*args, stage=stage, **kwargs)
            
            if stage == 'search':
                raise ValueError(f"Invalid stage: {stage}")
            elif stage == 'select':
                allowed_fields = ['playbook']
            elif stage == 'submit':
                allowed_fields = ['playbook', 'playbook_name', 'playbook_json']
            else:
                raise ValueError(f"Invalid stage: {stage}")
            self.fields = {key: self.fields[key] for key in allowed_fields}
        
        def clean_playbook(self) -> dict:
            value = super().clean_playbook()
            if self.stage == 'select' and value is not None:
                try:
                    data = json.loads(value.read())
                    return data
                except Exception as e:
                    self.add_error('playbook', str(e))
                    return None
    
    class MISPImportForm(ImportMixin, ImportForm):
        pass
    
    class KafkaImportForm(ImportMixin, ImportForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['search_field'].set_placeholder(_('"*" or any search term.'))
    
    class JSONExportForm(ExportForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            import sasp.models.cacao_1_1 as cacao_1_1
            if 'wiki_form' not in self.filter:
                self.filter['wiki_form'] = cacao_1_1.CACAO_1_1.cls_form
            
            self.fields['playbook'].queryset = Playbook.objects.filter(**self.filter)
            self.fields['playbook'].add_class('select2')
            self.fields['sanitization'].disabled = True
    
    class MISPExportForm(ExportForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            import sasp.models.cacao_1_1 as cacao_1_1
            if 'wiki_form' not in self.filter:
                self.filter['wiki_form'] = cacao_1_1.CACAO_1_1.cls_form
            
            self.fields['playbook'].queryset = Playbook.objects.filter(**self.filter)
            self.fields['playbook'].add_class('select2')
            self.fields['sanitization'].disabled = True
    
    class KafkaExportForm(ExportForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            import sasp.models.cacao_1_1 as cacao_1_1
            if 'wiki_form' not in self.filter:
                self.filter['wiki_form'] = cacao_1_1.CACAO_1_1.cls_form
            
            self.fields['playbook'].queryset = Playbook.objects.filter(**self.filter)
            self.fields['playbook'].add_class('select2')
            self.fields['sanitization'].disabled = True