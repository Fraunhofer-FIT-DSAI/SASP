from django import forms
from django.forms import formset_factory
from django.utils.translation import gettext as _

from sasp.models import Playbook,Playbook_Object
from sasp.wiki_interface import Wiki
from sasp.knowledge import KnowledgeBase
from .form_fields import CustomCharField, CustomModelChoiceField
from sasp.utils import wiki_name
import re
import json

knowledge_base = KnowledgeBase()

class PlaybookObjectForm(forms.Form):
    @staticmethod
    def validate_wiki_page_name(value):
        if not re.match(KnowledgeBase.regex_wiki_name, value):
            raise forms.ValidationError("Invalid wiki page name")
    @staticmethod
    def validate_wiki_page_name_unique(value):
        if Playbook_Object.objects.filter(wiki_page_name=value).exists():
            raise forms.ValidationError("Wiki page name already exists")
    
    system_wiki_page_name = CustomCharField(
        label="Wiki Page Name", 
        required=True, 
        help_text="A unique identifier for this object on the wiki. It should start capitalized and avoid special characters.",
        validators=[validate_wiki_page_name],
    )
    system_parent_playbook = forms.CharField(
        label="Parent Playbook",
        required=False,
    )
    system_parent_object = forms.ModelChoiceField(
        label="Parent Object",
        queryset=Playbook_Object.objects.all(),
        required=False,
        blank=True,
    )
    system_parent_object_field = forms.ChoiceField(
        label="Parent Object Field",
        required=False,
    )
    
    def __init__(self, *args, **kwargs):
        self.object_cls = kwargs.pop('object_cls')
        self.object = kwargs.pop('object')
        self.playbook_cls = kwargs.pop('playbook_cls')
        self.playbook = kwargs.pop('playbook')
        
        self.is_playbook = kwargs.pop('is_playbook', False)
        self.is_new = kwargs.pop('is_new', False)
        
        parent_object = kwargs.pop('parent_object', None)
        parent_field = kwargs.pop('parent_field', None)
        
        
        self.system_fields = [
            'system_wiki_page_name',
            'system_parent_playbook',
            'system_parent_object',
            'system_parent_object_field',
        ]
        
        super().__init__(*args, **kwargs)
        
        self.init_system_fields(parent_object, parent_field)
    
    def init_system_fields(self, parent_object, parent_field):
        self.fields['system_parent_playbook'].disabled = True
        if not self.is_playbook:
            self.fields['system_parent_playbook'].initial = self.playbook.get_label()
        
        if not self.is_new:
            self.fields['system_wiki_page_name'].disabled = True
            self.fields['system_parent_object'].disabled = True
            self.fields['system_parent_object_field'].disabled = True
        else:
            self.fields['system_wiki_page_name'].validators.append(self.validate_wiki_page_name_unique)
            self.fields['system_parent_object'].queryset = Playbook_Object.objects.filter(playbook=self.playbook)
        
        if self.is_playbook:
            self.fields['system_parent_object'].disabled = True
            self.fields['system_parent_object_field'].disabled = True
        
        if self.is_new and not self.is_playbook and parent_object:
            self.fields['system_parent_object'].initial = parent_object
            self.fields['system_parent_object_field'].choices = [
                (field.field_name, field.get_label())
                for field in parent_object.resolve_subclass().get_fields()
            ]
            if parent_field:
                self.fields['system_parent_object_field'].initial = parent_field
        
        if self.object.wiki_page_name:
            initial = self.object.wiki_page_name
        else:
            try:
                initial = self.object_cls.generate_wiki_name()
            except NotImplementedError:
                initial = None
        self.fields['system_wiki_page_name'].initial = initial
    
    def save(self):
        playbook = self.playbook
        if playbook.pk is None:
            playbook.wiki_page_name = self.object.wiki_page_name
            self.playbook.save()
        if self.object.pk is None:
            self.object.wiki_page_name = self.cleaned_data['system_wiki_page_name']
        self.object.content = self.object.content.update(
            {
                key: self.cleaned_data[key]
                for key in self.system_fields
                if key not in self.system_fields
            }
        )
        self.object.full_save()

class CACAO_1_1_PlaybookObjectForm(PlaybookObjectForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_key, field in self.object.get_form_fields().items():
            self.fields[field_key] = field
    
    def save(self):
        # Set wiki page name on objects
        if self.is_new:
            if self.is_playbook:
                self.playbook.wiki_page_name = self.cleaned_data['system_wiki_page_name']
            self.object.wiki_page_name = self.cleaned_data['system_wiki_page_name']
        
        for key, value in self.cleaned_data.items():
            if key in self.system_fields:
                continue
            if (
                getattr(self.fields[key],'empty_value', None) == value or 
                value in getattr(self.fields[key],'empty_values', [])
                ):
                self.object.clear_field(key)
            else:
                self.object.set_field(key, value)
        
        if self.is_playbook:
            self.playbook.save()
        self.object.full_save(skip_relations=True)
        
        if self.cleaned_data['system_parent_object'] and self.cleaned_data['system_parent_object_field']:
            parent_object = self.cleaned_data['system_parent_object'].resolve_subclass()
            parent_field = self.cleaned_data['system_parent_object_field']
            parent_object.add_to_field(parent_field, self.object.wiki_page_name)
            parent_object.full_save(skip_register=True, skip_relations=True)
        self.playbook.update_relations()

class ArchiveCreateForm(forms.Form):
    playbook = CustomModelChoiceField(
        label=_("Playbook"),
        queryset=Playbook.query(archived="False"),
        required=True,
    )
    archive_tag = CustomCharField(
        label=_("Archive Tag"),
        min_length=3,
        required=True,
    )
    
    def clean(self) -> dict:
        cleaned_data = super().clean()
        wiki_page_name = cleaned_data.get('playbook').wiki_page_name
        archive_tag = cleaned_data.get('archive_tag')
        if Playbook.query(wiki_page_name=wiki_page_name, archived="True", archive_tag=archive_tag).exists():
            raise forms.ValidationError({
                'archive_tag': [_("Archive tag already exists for this playbook")],
            })

class SearchForm(forms.Form):
    search = forms.CharField(label="Search", max_length=100)

    search.widget.attrs.update(
        {
            'class': 'form-control',
            'placeholder': 'Enter search term',
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        search = cleaned_data.get("search")
        if not search:
            raise forms.ValidationError("No search term entered")

class HiveDashboardForm(forms.Form):
    playbook_choice = forms.ChoiceField(label="Playbook", choices=[])
    case_choice = forms.ChoiceField(label="Case", choices=[])

    def __init__(self, *args, **kwargs):
        playbook_choices = kwargs.pop('playbook_choices', [])
        case_choices = kwargs.pop('case_choices', [])
        super().__init__(*args, **kwargs)

        self.fields['playbook_choice'].choices = [
            (playbook.pk, playbook.name)
            for playbook in playbook_choices
        ]

        self.fields['case_choice'].choices = [
            (case["caseID"], f"{case['title']} - {case['caseID']}")
            for case in case_choices
        ]

        for field in self.fields:
            self.fields[field].widget.attrs.update(
                {
                    'class': " ".join(['form-select', 'select2-single']),
                }
            )
        
    def clean(self):
        super().clean()

class NameEntryForm(forms.Form):
    name = forms.CharField(label="Name", max_length=100)

    name.widget.attrs.update(
        {
            'class': 'form-control',
            'placeholder': knowledge_base.messages.sharing.misp.import_.prompt_for_name__TXT(),
        }
    )

    def to_python(self, value):
        return wiki_name(value)

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        if not name:
            raise forms.ValidationError(knowledge_base.messages.sharing.misp.errors.import_.no_name__TXT())
        
        if Wiki().get_page_exists(wiki_name(name)):
            raise forms.ValidationError(knowledge_base.messages.sharing.misp.errors.import_.page_exists__TXT())
        
        disallowed_chars = ["/", "\\", ":", "*", "?", "\"", "<", ">", "|", "#", "[", "]", "(" ,")", "{", "}"]
        errors = []
        for char in disallowed_chars:
            if char in name:
                errors.append(forms.ValidationError(knowledge_base.messages.sharing.misp.errors.import_.invalid_name__TXT(char)))
        if errors:
            raise forms.ValidationError(errors)
        

class FileUploadForm(forms.Form):
    file_field = forms.FileField()
    file_field.widget.attrs.update(
        {
            'class': 'form-control',
            'id': 'file_field',
            # 'accept': '.json',
        }
    )

    def clean(self):
        super(FileUploadForm, self).clean()
        file = self.cleaned_data.get('file_field')
        if not file:
            raise forms.ValidationError("No file or empty file selected")
        if file.size > 2621440: # 2.5 MB
            raise forms.ValidationError("File size must be less than 2.5 MB")
        try:
            json.load(self.cleaned_data['file_field'])
        except json.decoder.JSONDecodeError:
            raise forms.ValidationError("File is not a valid JSON file")
        except Exception as _:
            raise forms.ValidationError("File is not a valid JSON file")

class ExportFormJson(forms.Form):
    choices = sorted([
        (key,level)
        for key,level in knowledge_base.tlp_levels.items()
    ])
    sanitization_choice = forms.ChoiceField(choices=choices, initial=choices[-1][0])

    sanitization_choice.widget.attrs.update(
        {
            'class': 'form-select',
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        try:
            cleaned_data['sanitization_choice'] = int(cleaned_data['sanitization_choice'])
        except ValueError:
            raise forms.ValidationError("Invalid sanitization choice")
        
class SwitchCaseForm(forms.Form):
    case_name = forms.CharField(required=False)
    case_name.widget.attrs.update(
        {
            'class': 'form-control',
            'placeholder': 'Enter value to match switch against.',
        }
    )
    step_list = forms.CharField(required=False)
    step_list.widget.attrs.update(
        {
            'class': 'form-control tokenfield',
            'placeholder': 'Enter step list e.g. step--1, step--2, step--3',
        }
    )

SwitchCaseFormSet = formset_factory(SwitchCaseForm, extra=5)

class FilterPlaybooksForm(forms.Form):
    filters = {
        'form_type' : None,
        'name' : None,
        'tags' : None, # Turn into list
        'author' : None,
        'confidentiality' : None # Expecteed as shape 'tlp:white'
    } # TODO Match with form
    form_choices = [
        ('','Any'),
        ('SAPPAN','SAPPAN'),
        ('CACAO','CACAO'),
    ]
    confidentiality_choices = [
        ('','Any'),
        ('white','TLP:WHITE'),
        ('green','TLP:GREEN'),
        ('amber','TLP:AMBER'),
        ('red','TLP:RED'),
    ]
        
    form_type = forms.ChoiceField(choices=form_choices, required=False, label="Standard")
    name = forms.CharField(required=False, label="Playbook Name")
    tags = forms.CharField(required=False, label="Tags (tag1, tag2, tag3)")
    author = forms.CharField(required=False, label="Author")
    confidentiality = forms.ChoiceField(choices=confidentiality_choices, required=False, label="Confidentiality")

    # With django-bootstrap5, the widgets should only need updating for js classes

    def clean(self):
        cleaned_data = super().clean()
        for key in cleaned_data:
            if key == 'form_type':
                continue
            if cleaned_data[key]:
                cleaned_data[key] = cleaned_data[key].strip().lower()
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        if tags:
            tags = [tag.strip() for tag in tags.split(',')]
        return tags
        