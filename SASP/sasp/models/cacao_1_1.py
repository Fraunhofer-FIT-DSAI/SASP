from . import Playbook, Playbook_Object, Semantic_Relation
from sasp.pytools import classproperty
import sasp.bpmn_util
import sasp.wiki_interface
import sasp.knowledge
import sasp.forms.form_fields as form_fields
import sasp.forms as forms

from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
import django.forms.widgets as widgets

from datetime import datetime
from datetime import timezone as dt_timezone
import uuid
import json
import re
import enum
import base64


class FT(enum.Enum):
    string = enum.auto()
    integer = enum.auto()
    boolean = enum.auto()
    timestamp = enum.auto()
    identifier = enum.auto()
    list_ = enum.auto()
    dictionary = enum.auto()
    object_list = enum.auto()
    object_dict = enum.auto()
    
    contact = enum.auto()
    civic_location = enum.auto()
    gps_location = enum.auto()
    target = enum.auto()
    external_reference = enum.auto()
    marking_definition = enum.auto()
    variable = enum.auto()
    workflow_step = enum.auto()
    extension_definition = enum.auto()
    signature = enum.auto()
    command = enum.auto()
    playbook = enum.auto()
    
    def __str__(self):
        return f'{self.name}'
    
    def obj_map(self):
        return {
            FT.contact: CACAO_1_1_ContactInformation,
            FT.civic_location: CACAO_1_1_CivicLocation,
            FT.gps_location: CACAO_1_1_GpsLocation,
            FT.target: CACAO_1_1_Target,
            FT.external_reference: CACAO_1_1_ExternalReference,
            FT.marking_definition: CACAO_1_1_DataMarking,
            FT.variable: CACAO_1_1_Variable,
            FT.workflow_step: CACAO_1_1_Step_Object,
            FT.extension_definition: CACAO_1_1_Extension,
            FT.signature: CACAO_1_1_Signature,
            FT.command: CACAO_1_1_Command,
            FT.playbook: CACAO_1_1_Playbook
        }
    def is_object(self):
        return self in self.obj_map()
    def get_object(self):
        return self.obj_map()[self]
    def id_to_wiki(self, id):
        if self != FT.identifier:
            raise ValueError(f"Expected FT.identifier, got {self}")
        name_, uuid_ = id.split("--", 1)
        name_ = re.sub(sasp.knowledge.KnowledgeBase.regex_wiki_name_disallowed, "", name_)
        uuid_ = re.sub(sasp.knowledge.KnowledgeBase.regex_wiki_name_disallowed, "", uuid_)
        name_ = name_[0].capitalize() + name_[1:]
        return f"{name_}--{uuid_}"
    def wiki_to_id(self, wiki_name):
        if self != FT.identifier:
            raise ValueError(f"Expected FT.identifier, got {self}")
        return wiki_name.replace(" ", "_").lower()
    def smw_get_type(self):
        # Page, Text, Boolean, Number
        return {
            FT.string: "Text",
            FT.integer: "Number",
            FT.boolean: "Boolean",
            FT.timestamp: "Text",
            FT.identifier: "Page",
            FT.list_: "Text",
            FT.dictionary: "Text",
            FT.object_list: "Page",
            FT.object_dict: "Page",
            FT.contact: "Page",
            FT.civic_location: "Page",
            FT.gps_location: "Page",
            FT.target: "Page",
            FT.external_reference: "Page",
            FT.marking_definition: "Page",
            FT.variable: "Page",
            FT.workflow_step: "Page",
            FT.extension_definition: "Page",
            FT.signature: "Page",
            FT.command: "Page",
            FT.playbook: "Page",
        }.get(self, "Text")
    def smw_is_list(self):
        return self in [FT.list_, FT.object_list, FT.object_dict]


class CACAO_1_1(Playbook):
    class Meta:
        proxy = True
    class Deserializer(Playbook.Deserializer):
        class DeserializationException(Playbook.Deserializer.DeserializationException):
            pass
        class DeserializerMissingNameException(DeserializationException):
            pass
        class DeserializationDuplicateError(DeserializationException):
            pass
        
        @classmethod
        def supported(cls) -> bool:
            """Returns whether the deserializer is supported by the current environment."""
            return True
        
        def __init__(self, json_data):
            self.json_data = json_data
            self.objects = None
            self.playbook = None
        def new_object(self, obj):
            obj.playbook = self.playbook
            self.objects.append(obj)
        def validate(self):
            valid,errors = CACAO_1_1_Playbook.validate_json(self.json_data)
            try:
                self.deserialize()
            except self.DeserializationException as e:
                valid = False
                errors.append((str(e), "critical", None))
            return valid, errors
        def deserialize(self, name=None):
            self.objects = []
            self.playbook = CACAO_1_1(
                wiki_form=CACAO_1_1_Playbook.cls_form,
            )
            if not name:
                name = self.json_data.get(CACAO_1_1_Playbook.Field_Name.cacao_name)
            name = CACAO_1_1_Playbook.generate_wiki_name(name=name)
            if not name:
                raise self.DeserializerMissingNameException("Name is required for import")
            self.playbook.wiki_page_name = name
            self.playbook.name = name
            self.objects = [
                CACAO_1_1_Playbook(
                    playbook=self.playbook,
                    wiki_form=CACAO_1_1_Playbook.cls_form,
                    wiki_page_name=name,
                )
            ]
            self.objects[0].deserialize_object(self.json_data, self)
            # self.objects gets filled with all objects in the playbook
            existing_wiki_pages = Playbook_Object.objects.filter(archived=False).values_list('wiki_page_name', flat=True)
            existing_wiki_pages = set(x.casefold() for x in existing_wiki_pages)
            for obj in self.objects:
                obj_name = obj.wiki_page_name.casefold()
                if obj_name in existing_wiki_pages:
                    raise self.DeserializationDuplicateError(f"Object name '{obj.wiki_page_name}' is already in use.")
                existing_wiki_pages.add(obj_name)
            self.objects = [obj.resolve_subclass() for obj in self.objects]
        
        def save(self):
            wiki = sasp.wiki_interface.Wiki()
            
            self.playbook.save()
            for obj in self.objects:
                obj.full_save(skip_register=True,skip_relations=True, wiki=wiki)
            self.playbook.update_relations()
    
    regex_timestamp = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
    regex_identifier = r'^[a-z\-]+--[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$'
    cls_form = "CACAO 1-1 Playbook"
    cls_label = "CACAO 1.1 Playbook"
    
    @classproperty
    def slug(cls) -> str:
        """Returns the slug of the object."""
        if cls.cls_form:
            return cls.cls_form.replace(" ", "-").lower()
        else:
            return None
    
    _playbook_object_class = None
    @classproperty
    def playbook_object_class(cls):
        return CACAO_1_1_PlaybookObject
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wiki_form = self.cls_form
    
    def get_name(self):
        try:
            return self.get_root().name
        except Exception:
            pass
        return self.name or self.wiki_page_name
    
    def serialize(self):
        return self.get_root().serialize_object()
    
    def remove(self, *args, **kwargs):
        skip_wiki = kwargs.pop("skip_wiki", False)
        if not skip_wiki:
            wiki = sasp.wiki_interface.Wiki()
            
        for obj in self.playbook_objects.all():
            obj.resolve_subclass().remove(
                wiki=wiki, 
                skip_wiki=skip_wiki, 
                skip_deregister=True, 
                skip_relations=True,
                skip_db_delete=True
            )
        self.delete(*args, **kwargs)
    
    def bpmn(self):
        bpmn_xml,error_list = sasp.bpmn_util.generate_bpmn_cacao_1_1(self)
        sasp.wiki_interface.Wiki().set_bpmn(self.wiki_page_name,bpmn_xml)
        return bpmn_xml,error_list
    
    def update_relations(self):
        relations = []
        sem_relation_list = []
        Semantic_Relation.objects.filter(playbook=self).delete()
        obj_dict = {obj.wiki_page_name:obj.resolve_subclass() for obj in self.playbook_objects.all()}
        for obj in obj_dict.values():
            relations += obj.make_relations(obj)
        for subject,predicate,object_ in relations:
            if subject in obj_dict and object_ in obj_dict:
                sem_relation_list.append(Semantic_Relation(
                    subject_field=obj_dict[subject],
                    predicate=predicate,
                    object_field=obj_dict[object_],
                    playbook=self
                ))
        Semantic_Relation.objects.bulk_create(sem_relation_list)
    
    
    @classmethod
    def get_cls_label(cls):
        """Returns a human readable label for the form of the playbook."""
        return cls.cls_label if cls.cls_label else cls.cls_form
    
    @classmethod
    def get_properties(cls) -> list:
        """Returns all properties used in the CACAO 1.1 playbook."""
        subclasses = [CACAO_1_1_PlaybookObject]
        classes_list = []
        while subclasses:
            subclass = subclasses.pop()
            if not subclass.cls_form:
                subclasses += subclass.__subclasses__()
            else:
                classes_list.append(subclass)
        property_list = []
        for subcls in classes_list:
            for field in subcls.object_fields.values():
                property_list.append(field.get_prop_dict())
        return property_list
    
    @classmethod
    def get_templates(cls) -> dict:
        """Returns all templates used by the class."""
        return_dict = {}
        
        subclasses = [CACAO_1_1_PlaybookObject]
        classes_list = []
        while subclasses:
            subclass = subclasses.pop()
            if not subclass.cls_form:
                subclasses += subclass.__subclasses__()
            else:
                classes_list.append(subclass)
        
        for subcls in classes_list:
            return_dict[subcls.cls_form] = subcls.get_template()
        return return_dict
        
    @classmethod
    def get_root_class(cls):
        return CACAO_1_1_Playbook
    
    def register_object(self, new_object):
        root:CACAO_1_1_Playbook = self.get_root()
        root.register_object(new_object)
        root.full_save(skip_register=True, skip_relations=True)
    def deregister_object(self, old_object):
        root:CACAO_1_1_Playbook = self.get_root()
        root.deregister_object(old_object)
        root.full_save(skip_register=True, skip_relations=True)
    
    def get_fields_context(self):
        return self.get_root().get_fields_context()
    
    def get_absolute_url(self):
        return reverse('playbook-detail', kwargs={'pk': self.pk})
    
    def get_edit_url(self):
        return reverse('playbook_object-edit', kwargs={'pk': self.get_root().pk, 'pk_pb': self.pk})
    
    def get_delete_url(self):
        return reverse('playbook-delete', kwargs={'pk': self.pk})
    
    @classmethod
    def is_json_representation(cls, json_data):
        """Checks if the provided JSON data represents a playbook of this type."""
        if (
            json_data.get(CACAO_1_1_Playbook.Field_Type.cacao_name) in ["playbook", "playbook-template"] and
            json_data.get(CACAO_1_1_Playbook.Field_SpecVersion.cacao_name) == "1.1"
        ):
            return True
        return False
    
    @classmethod
    def new_from_json(cls, json_data):
        """Creates a new playbook from the provided JSON data."""
        deserializer = cls.Deserializer(json_data)
        deserializer.deserialize()
        deserializer.save()
        return deserializer.playbook
    
class CACAO_1_1_PlaybookObject(Playbook_Object):
    cls_form = None
    cls_label = "CACAO 1.1 Playbook Object"
    object_fields = {}
    object_fields_by_name = {}
    priority:int = 0
        
    @classproperty
    def is_root(cls):
        return False
    @classproperty
    def slug(cls) -> str:
        """Returns the slug of the object."""
        if cls.cls_form:
            return cls.cls_form.replace(" ", "-").lower()
        else:
            return None
    
    _playbook_class = None
    @classproperty
    def playbook_class(cls):
        return CACAO_1_1
    
    
    
    class Object_Field(Playbook_Object.Object_Field):
        class Exception_Field_Validation(ValidationError):
            pass
        field_type:FT = None
        required:bool = False
        field_name:str = None
        prop_name:str = None
        cacao_name:str = None
        label:str = None
        help_text:str = ''
        iterable_type:FT = None
        allowed_values:list = None
        possible_values:list = None
        identifier_prefix:str = None
        placeholder:str = None
        text_area:bool = False
        contains_keys:bool = False
        hidden:bool = False
        is_list:bool = False
        priority:int = 0
        
        @classmethod
        def get_label(cls):
            return cls.label if cls.label else cls.field_name
        
        @classmethod
        def get_prop_name(cls):
            return cls.prop_name if cls.prop_name else cls.field_name
        
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.prop_name if cls.prop_name else cls.field_name,
                "label": cls.get_label(),
                "type": cls.field_type.smw_get_type(),
                "list": cls.field_type.smw_is_list(),
            }
        
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            if wiki_data.get(cls.get_prop_name(), []) == []: # Skip empty fields
                return
            if cls.field_type.smw_get_type() == "Page":
                if cls.field_type.smw_is_list():
                    cls.set_field(obj, [x['fulltext'] for x in wiki_data[cls.get_prop_name()]])
                else:
                    cls.set_field(obj, wiki_data[cls.get_prop_name()]['fulltext'][0])
            elif cls.field_type == FT.dictionary:
                cls.set_field(obj, 
                    json.loads(
                        base64.b64decode(
                            wiki_data[cls.get_prop_name()][0]
                        ).decode('utf-8')
                    )
                )
            elif cls.field_type == FT.boolean:
                val = wiki_data[cls.get_prop_name()][0]
                cls.set_field(obj, True if val == "t" else False)
            else:
                if cls.field_type in [FT.list_, FT.object_list, FT.object_dict]:
                    val = wiki_data[cls.get_prop_name()]
                else:
                    val = wiki_data[cls.get_prop_name()][0]
                cls.set_field(obj, wiki_data[cls.get_prop_name()])
        
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.field_type == FT.boolean:
                wiki_dict['content'][cls.get_prop_name()] = "Yes" if value else "No"
            elif cls.field_type in [FT.list_, FT.object_list, FT.object_dict]:
                if cls.iterable_type == FT.boolean:
                    wiki_dict['content'][cls.get_prop_name()] = ",".join("Yes" if x else "No" for x in value)
                else:
                    wiki_dict['content'][cls.get_prop_name()] = ",".join(str(x) for x in value)
            elif cls.field_type == FT.dictionary:
                wiki_dict['content'][cls.get_prop_name()] = base64.b64encode(json.dumps(value).encode('utf-8')).decode('utf-8')
            return wiki_dict
        
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            if cls.field_type == FT.list_:
                if cls.iterable_type is None:
                    raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
                if cls.iterable_type == FT.identifier:
                    return {cls.cacao_name: [FT.identifier.wiki_to_id(x) for x in cls.get_field(obj)]}
                elif cls.iterable_type == FT.integer:
                    return {cls.cacao_name: [int(x) for x in cls.get_field(obj)]}
                elif cls.iterable_type == FT.boolean:
                    return {cls.cacao_name: [True if x == "Yes" else False for x in cls.get_field(obj)]}
                elif cls.iterable_type == FT.string:
                    return {cls.cacao_name: cls.get_field(obj)}
                else:
                    raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
            
            if cls.field_type == FT.object_list:
                if cls.iterable_type is None:
                    raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
                if cls.iterable_type.is_object():
                    json_dict = []
                    for sub_obj in cls.get_field(obj):
                        pbo = obj.playbook.playbook_objects.filter(wiki_page_name=sub_obj).first()
                        pbo = pbo.resolve_subclass()
                        json_dict.append(pbo.serialize_object())
                    return {cls.cacao_name: json_dict}
                else:
                    raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
            
            if cls.field_type == FT.object_dict:
                if cls.iterable_type is None:
                    raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
                if cls.iterable_type.is_object():
                    json_dict = {}
                    for sub_obj in cls.get_field(obj):
                        pbo = obj.playbook.playbook_objects.filter(wiki_page_name=sub_obj).first()
                        pbo = pbo.resolve_subclass()
                        json_dict[pbo.get_cacao_id()] = pbo.serialize_object()
                    return {cls.cacao_name: json_dict}
                else:
                    raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
            
            
            if cls.field_type == FT.dictionary:
                return {cls.cacao_name: cls.get_field(obj)}
            
            if cls.field_type == FT.identifier:
                return {cls.cacao_name: FT.identifier.wiki_to_id(cls.get_field(obj))}
            elif cls.field_type in [FT.integer, FT.boolean, FT.string, FT.timestamp]:
                return {cls.cacao_name: cls.get_field(obj)}
            elif cls.field_type.is_object():
                pbo = obj.playbook.playbook_objects.filter(wiki_page_name=cls.get_field(obj)).first()
                pbo = pbo.resolve_subclass()
                return {cls.cacao_name: pbo.serialize_object()}
            else:
                raise NotImplementedError(f"No serialization method for field {cls.get_label()}")
        
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            if cls.field_type == FT.list_:
                if cls.iterable_type is None:
                    raise NotImplementedError(f"No deserialization method for field {cls.get_label()}")
                if cls.iterable_type == FT.identifier:
                    cls.add_to_field(obj, [
                        FT.identifier.id_to_wiki(x) for x in data[cls.cacao_name]
                        for x in data[cls.cacao_name]
                        ]
                    )
                elif cls.iterable_type == FT.integer:
                    cls.add_to_field(obj, [str(x) for x in data[cls.cacao_name]])
                elif cls.iterable_type == FT.boolean:
                    cls.set_field(obj, data[cls.cacao_name])
                elif cls.iterable_type == FT.string:
                    cls.add_to_field(obj, data[cls.cacao_name])
                elif cls.iterable_type == FT.timestamp:
                    cls.add_to_field(obj, data[cls.cacao_name])
                else:
                    raise NotImplementedError(f"No deserialization method for field {cls.get_label()}")
            elif cls.field_type == FT.object_list:
                if cls.iterable_type.is_object():
                    ids = []
                    for sub_obj in data[cls.cacao_name]:
                        sub_cls = cls.iterable_type.get_object()
                        if hasattr(sub_cls, 'get_subclass'):
                            sub_cls = sub_cls.get_subclass(
                                sub_obj.get(sub_cls.Field_Type.cacao_name)
                            )
                        id = sub_cls.generate_wiki_name()
                        new_obj = sub_cls(
                            wiki_page_name=id,
                            wiki_form=sub_cls.cls_form,
                        )
                        new_obj = new_obj.resolve_subclass()
                        new_obj.deserialize_object(sub_obj,deserializer)
                        deserializer.new_object(new_obj)
                        ids += [id]
                    cls.add_to_field(obj, ids)
            elif cls.field_type == FT.object_dict:
                if cls.iterable_type.is_object():
                    ids = []
                    for cacao_id, sub_obj in data[cls.cacao_name].items():
                        sub_cls = cls.iterable_type.get_object()
                        if hasattr(sub_cls, 'get_subclass'):
                            sub_cls = sub_cls.get_subclass(
                                sub_obj.get(sub_cls.Field_Type.cacao_name)
                            )
                        id = sub_cls.generate_wiki_name(name=cacao_id)
                        new_obj = sub_cls(
                            wiki_page_name=id,
                            wiki_form=sub_cls.cls_form,
                        )
                        new_obj = new_obj.resolve_subclass()
                        new_obj.deserialize_object(sub_obj,deserializer)
                        deserializer.new_object(new_obj)
                        ids.append(id)
                    cls.add_to_field(obj, ids)
                else:
                    raise NotImplementedError(f"No deserialization method for field {cls.get_label()}")
            elif cls.field_type == FT.identifier:
                cls.add_to_field(obj, FT.identifier.id_to_wiki(data[cls.cacao_name]))
            elif cls.field_type in [FT.integer, FT.boolean, FT.string, FT.timestamp]:
                cls.add_to_field(obj, data[cls.cacao_name])
            elif cls.field_type.is_object():
                sub_cls = cls.field_type.get_object()
                sub_obj = data[cls.cacao_name]
                if hasattr(sub_cls, 'get_subclass'):
                    sub_cls = sub_cls.get_subclass(
                        sub_obj.get(sub_cls.Field_Type.cacao_name)
                    )
                id = sub_cls.generate_wiki_name()
                new_obj = Playbook_Object(
                    wiki_page_name=id,
                    wiki_form=sub_cls.cls_form,
                )
                new_obj = new_obj.resolve_subclass()
                new_obj.deserialize_object(sub_obj,deserializer)
                deserializer.new_object(new_obj)
                cls.add_to_field(obj, id)
            else:
                raise NotImplementedError(f"No deserialization method for field {cls.get_label()}")

        # NOTE: We assume data in our db to be correct, and accept faulty exports
        # With this structure where every object gets a subclass, we should write validators for input
        # during object creation via the GUI as well, but one thing at a time
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                     "error",
                     (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.field_type is None:
                raise NotImplementedError(f"No validation method for field {cls.get_label()}")
            # Cover basic type checks - dict, list, bool, int, str, identifier, timestamp
            if ((cls.field_type == FT.dictionary or cls.field_type == FT.object_dict) 
                and not isinstance(data.get(cls.cacao_name), dict)):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a dictionary", 
                     "critical",
                     (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors # On critical error, abort. Could lead to integrity issues
            if ((cls.field_type == FT.list_ or cls.field_type == FT.object_list) 
                and not isinstance(data.get(cls.cacao_name), list)):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a list", 
                     "critical",
                     (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            if cls.field_type in [FT.list_, FT.dictionary, FT.object_list]:
                value_type = cls.iterable_type
                value_list = data.get(cls.cacao_name)
            elif cls.field_type == FT.object_dict:
                value_type = cls.iterable_type
                value_list = data.get(cls.cacao_name).values()
            else:
                value_type = cls.field_type
                value_list = [data.get(cls.cacao_name)]
            for value in value_list:
                if value_type == FT.boolean and not isinstance(value, bool):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a boolean", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(value))
                        )
                    )
                    return valid, errors
                elif value_type == FT.integer and not isinstance(value, int):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be an integer", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(value))
                        )
                    )
                    return valid, errors
                elif value_type == FT.string and not isinstance(value, str):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a string", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(value))
                        )
                    )
                    return valid, errors
                elif value_type == FT.identifier:
                    if not isinstance(value,str):
                        valid = False
                        errors.append(
                            (f"Field '{cls.cacao_name}' must be a string",
                            "critical",
                            (json.dumps(data), cls.cacao_name, json.dumps(value)))
                        )
                        return valid, errors
                    if not re.match(
                        CACAO_1_1.regex_identifier, 
                        value):
                        errors.append(
                            (f"Field '{cls.cacao_name}' must be an identifier", 
                            "error",
                            (json.dumps(data), cls.cacao_name, json.dumps(value))
                            )
                        )
                    if cls.identifier_prefix and not value.startswith(cls.identifier_prefix):
                        errors.append(
                            (f"Field '{cls.cacao_name}' must start with '{cls.identifier_prefix}'", 
                            "error",
                            (json.dumps(data), cls.cacao_name, json.dumps(value))
                            )
                        )
                elif value_type == FT.timestamp:
                    if not isinstance(value,str):
                        valid = False
                        errors.append(
                            (f"Field '{cls.cacao_name}' must be a string",
                            "critical",
                            (json.dumps(data), cls.cacao_name, json.dumps(value))
                        )
                        )
                        return valid, errors
                    if not re.match(
                    # yyyy-mm-ddThh:mm:ss[.s+]Z 
                    CACAO_1_1.regex_timestamp,
                    value):
                        errors.append(
                            (f"Field '{cls.cacao_name}' must be a timestamp", 
                            "error",
                            (json.dumps(data), cls.cacao_name, json.dumps(value))
                            )
                        )
                if value_type.is_object():
                    sub_cls = value_type.get_object()
                    if hasattr(sub_cls, 'get_subclass'):
                        sub_cls = sub_cls.get_subclass(value.get(sub_cls.Field_Type.cacao_name))
                    valid, obj_errors = sub_cls.validate_json(value)
                    errors += obj_errors
                    if not valid:
                        return valid, errors
                if cls.allowed_values is not None and value not in cls.allowed_values:
                    errors.append(
                    (f"Field '{cls.cacao_name}' must be one of {cls.allowed_values}", 
                    "error",
                    (json.dumps(data), cls.cacao_name, json.dumps(value))
                    )
                )
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            raise NotImplementedError("validate_field not implemented")
        @classmethod
        def validate_field_warnings(cls, obj):
            return []
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def add_to_field(cls,obj,value):
            if cls.is_list:
                cls.set_field(obj, cls.get_field(obj, []) + [value])
            else:
                cls.set_field(obj, value)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def remove_from_field(cls, obj, value):
            if not obj.content.get(cls.field_name):
                return
            if cls.field_type in [FT.list_, FT.object_list, FT.object_dict]:
                try:
                    obj.content[cls.field_name].remove(value)
                except ValueError:
                    pass
            elif cls.field_type == FT.dictionary:
                obj.content[cls.field_name].pop(value, None)
            else:
                obj.content.pop(cls.field_name, None)
        @classmethod
        def initial_fill(cls, obj=None):
            if cls.allowed_values and len(cls.allowed_values) == 1:
                return cls.allowed_values[0]
            if obj:
                if cls.is_list:
                    return cls.get_field(obj, [])
                return cls.get_field(obj)
            return None
        @classmethod
        def get_context(cls, *args, **kwargs):
            raise NotImplementedError(f"get_context not implemented for {cls.__name__}")
        
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            raise NotImplementedError(f"get_form_field not implemented for {cls.__name__}")
        
        @classmethod
        def prepare_form_field(cls, field_cls, *args, **kwargs):
            kwargs['label'] = kwargs.get('label', cls.get_label())
            kwargs['required'] = kwargs.get('required', cls.required)
            kwargs['help_text'] = kwargs.get('help_text', cls.help_text)
            kwargs['validators'] = kwargs.get('validators', [cls.validate_field])
            field_placeholder = kwargs.pop('placeholder', cls.placeholder if cls.placeholder else kwargs["label"])
            field = field_cls(**kwargs)
            field.set_placeholder(field_placeholder)
            return field
    
    class Hidden_Field(Object_Field):
        hidden = True
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            # Hidden Fields are used for metadata on the wiki, they don't get saved in the database
            pass
        
        @classmethod
        def write_to_wiki(cls, obj, value_=None):
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value_:
                return wiki_dict
            if cls.is_list:
                wiki_dict['content'][cls.get_prop_name()] = ",".join(value_)
            else:
                wiki_dict['content'][cls.get_prop_name()] = value_
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            return {} #Hidden fields are not exported
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            pass
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            pass
        @classmethod
        def set_field(cls, obj, value):
            raise ValueError("Attempted to set field on hidden field.")
        @classmethod
        def get_field(cls, obj, *args, **kwargs):
            raise ValueError("Attempted to get field on hidden field")
        @classmethod
        def clear_field(cls, obj):
            raise ValueError("Attempted to clear field on hidden field")
        @classmethod
        def get_context(cls, *args, **kwargs):
            return None
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            return None
    class Boolean_Field(Object_Field):
        field_type = FT.boolean
        is_list = False
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            
            def coerce(value):
                if value.lower() == "true" or value.lower() == "yes":
                    return True
                elif value.lower() == "false" or value.lower() == "no":
                    return False
                raise ValidationError(f"Invalid boolean value in field {cls.get_label()}")
            
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.CustomTypedListField,
                    coerce=coerce,
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.CustomBooleanField,
                    required=False, # Unchecked checkboxes = False, so we always get a value
                )
            return field_name, field
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.prop_name if cls.prop_name else cls.field_name,
                "label": cls.get_label(),
                "type": 'Boolean',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            if not values:
                return
            if any(x not in ['t','f'] for x in values):
                raise ValueError(f"Invalid boolean value in field {cls.get_label()}") # Should never happen, but best to catch it early
            values = [x == 't' for x in values]
            if not cls.is_list:
                values = values[0]
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                wiki_dict['content'][cls.get_prop_name()] = ",".join("Yes" if val else "No" for val in value)
            else:
                wiki_dict['content'][cls.get_prop_name()] = "Yes" if value else "No"
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            return {cls.cacao_name: cls.get_field(obj)}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            cls.set_field(obj, data[cls.cacao_name])
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                     "error",
                     (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                         "critical",
                         (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                if not all(isinstance(x, bool) for x in data.get(cls.cacao_name)):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list of boolean", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
            else:
                if not isinstance(data.get(cls.cacao_name), bool):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a boolean", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if cls.is_list:
                if not isinstance(value, list) and not all(isinstance(x, bool) for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of boolean")
            else:
                if not isinstance(value, bool):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a boolean")
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            if cls.is_list:
                return {
                    "type": "List",
                    'label': cls.get_label(),
                    "entries": [{
                        "type": "Boolean",
                        "text": str(x),
                    } for x in cls.get_field(obj)]
                }
            return {
                "type": "Boolean",
                'label': cls.get_label(),
                "text": str(cls.get_field(obj)),
            }
    class Integer_Field(Object_Field):
        field_type = FT.integer
        max_value = None
        min_value = None
        step_size = None
        is_list = False
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.CustomTypedListField,
                    coerce=int,
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.CustomIntegerField,
                    min_value=cls.min_value,
                    max_value=cls.max_value,
                    step_size=cls.step_size,
                )
            return field_name, field
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.prop_name if cls.prop_name else cls.field_name,
                "label": cls.get_label(),
                "type": 'Number',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                wiki_dict['content'][cls.get_prop_name()] = ",".join(str(val) for val in value)
            else:
                wiki_dict['content'][cls.get_prop_name()] = str(value)
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            return {cls.cacao_name: cls.get_field(obj)}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            cls.set_field(obj, data[cls.cacao_name])
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                     "error",
                     (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                         "critical",
                         (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                if not all(isinstance(x, int) for x in data.get(cls.cacao_name)):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list of integers", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
            else:
                if not isinstance(data.get(cls.cacao_name), int):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be an integer", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if cls.is_list:
                if not isinstance(value, list) and not all(isinstance(x, int) for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of integers")
                if cls.allowed_values and not all(x in cls.allowed_values for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of integers in {cls.allowed_values}")
                if cls.min_value is not None and not all(x >= cls.min_value for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of integers greater than or equal to {cls.min_value}")
                if cls.max_value is not None and not all(x <= cls.max_value for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of integers less than or equal to {cls.max_value}")
                if cls.step_size is not None and not all(x % cls.step_size == 0 for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of integers divisible by {cls.step_size}")
            else:
                if not isinstance(value, int):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be an integer")
                if cls.allowed_values and value not in cls.allowed_values:
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be an integer in {cls.allowed_values}")
                if cls.min_value is not None and value < cls.min_value:
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be greater than or equal to {cls.min_value}")
                if cls.max_value is not None and value > cls.max_value:
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be less than or equal to {cls.max_value}")
                if cls.step_size is not None and value % cls.step_size != 0:
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be divisible by {cls.step_size}")
        @classmethod
        def validate_field_warnings(cls, obj):
            return []
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            if cls.is_list:
                return {
                    "type": "List",
                    'label': cls.get_label(),
                    "entries": [{
                        "type": "Integer",
                        "text": str(x),
                    } for x in cls.get_field(obj)]
                }
            return {
                "type": "Integer",
                'label': cls.get_label(),
                "text": str(cls.get_field(obj)),
            }
    class String_Field(Object_Field):
        field_type = FT.string
        is_list = False
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            
            if cls.is_list:
                if cls.allowed_values:
                    field = cls.prepare_form_field(
                        form_fields.CustomMultipleChoiceField,
                        choices=[(x, x) for x in cls.allowed_values],
                    )
                elif cls.possible_values:
                    field = cls.prepare_form_field(
                        form_fields.CustomTokenListField,
                        coerce=str,
                        choices=[(x, x) for x in cls.possible_values],
                    )
                else:
                    field = cls.prepare_form_field(
                        form_fields.CustomTokenListField,
                        coerce=str,
                    )
            else:
                if cls.allowed_values:
                    field = cls.prepare_form_field(
                        form_fields.CustomChoiceField,
                        choices=[(x, x) for x in cls.allowed_values],
                    )
                else:
                    if cls.text_area:
                        field = cls.prepare_form_field(
                            form_fields.CustomCharField,
                            widget=widgets.Textarea,
                        )
                    else:
                        field = cls.prepare_form_field(
                            form_fields.CustomCharField,
                        )
            return field_name, field
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.prop_name if cls.prop_name else cls.field_name,
                "label": cls.get_label(),
                "type": 'Text',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                wiki_dict['content'][cls.get_prop_name()] = ",".join(str(val) for val in value)
            else:
                wiki_dict['content'][cls.get_prop_name()] = str(value)
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            return {cls.cacao_name: cls.get_field(obj)}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            cls.set_field(obj, data[cls.cacao_name])
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                     "error",
                     (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                         "critical",
                         (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                if not all(isinstance(x, str) for x in data.get(cls.cacao_name)):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list of strings", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
            else:
                if not isinstance(data.get(cls.cacao_name), str):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a string", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if cls.is_list:
                if not isinstance(value, list) and not all(isinstance(x, str) for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of strings")
                if cls.allowed_values and not all(x in cls.allowed_values for x in value):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of strings in {cls.allowed_values}")
            else:
                if not isinstance(value, str):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a string")
                if cls.allowed_values and value not in cls.allowed_values:
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a string in {cls.allowed_values}")
        @classmethod
        def validate_field_warnings(cls, obj):
            return []
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            if cls.is_list:
                return_dict = {
                    'type': 'List',
                    'label': cls.get_label(),
                    'entries': []
                }
                for x in cls.get_field(obj):
                    if cls.contains_keys and obj_dict and x in obj_dict:
                        return_dict['entries'].append({
                            'type': 'Href',
                            'text': obj_dict[x]['name'],
                            'href': obj_dict[x]['url']
                    })
                    else:
                        return_dict['entries'].append({
                            'type': 'String',
                            'text': str(x),
                        })
                return return_dict
            return {
                "type": "String",
                'label': cls.get_label(),
                "text": str(cls.get_field(obj)),
            }
    class Timestamp_Field(Object_Field):
        field_type = FT.timestamp
        is_list = False
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.CustomTypedListField,
                    coerce=str,
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.CustomTimestampField
                )
            return field_name, field
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.get_prop_name(),
                "label": cls.get_label(),
                "type": 'Text',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                wiki_dict['content'][cls.get_prop_name()] = ",".join(str(val) for val in value)
            else:
                wiki_dict['content'][cls.get_prop_name()] = str(value)
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            return {cls.cacao_name: cls.get_field(obj)}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            cls.set_field(obj, data[cls.cacao_name])
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                     "error",
                     (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                         "critical",
                         (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                value_list = data.get(cls.cacao_name)
            else:
                value_list = [data.get(cls.cacao_name)]
        
            if not all(isinstance(x, str) and re.match(CACAO_1_1.regex_timestamp, x) for x in value_list):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a list of timestamps",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if cls.is_list:
                if not isinstance(value, list):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list")
                value_list = value
            else:
                value_list = [value]
            
            if not all(isinstance(x, str) and re.match(CACAO_1_1.regex_timestamp, x) for x in value_list):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be timestamps")
            if cls.allowed_values and not all(x in cls.allowed_values for x in value):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be  in {cls.allowed_values}")
        @classmethod
        def validate_field_warnings(cls, obj):
            return []
        @classmethod
        def set_field(cls, obj, value):
            if isinstance(value, datetime):
                value = value.astimezone(dt_timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds') + 'Z'
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            return_dict = {}
            if cls.is_list:
                return_dict["type"] = "List"
                return_dict["label"] = cls.get_label()
                return_dict["entries"] = []
                for x in cls.get_field(obj):
                    return_dict["entries"].append({
                        "type": "Timestamp",
                        "text": str(x),
                    })
                return return_dict
            return {
                "type": "Timestamp",
                'label': cls.get_label(),
                "text": str(cls.get_field(obj)),
            }
        @classmethod
        def initial_fill(cls, obj=None):
            if cls.is_list:
                if obj:
                    return cls.get_field(obj, [])
                return []
            else:
                if obj and cls.get_field(obj):
                    try:
                        iso_string = cls.get_field(obj)[:-1] # Remove Z
                        datetm = datetime.fromisoformat(iso_string) # Load the datetime
                        datetm = datetm.astimezone(dt_timezone.utc) # Mark as UTC
                        return datetm
                    except Exception as _:
                        return None
                return None
    class Identifier_Field(Object_Field):
        field_type = FT.identifier
        is_list = False
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.CustomTokenListField,
                )
            elif cls.allowed_values:
                field = cls.prepare_form_field(
                    form_fields.CustomChoiceField,
                    choices=[(x, x) for x in cls.allowed_values],
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.CustomCharField
                )
            return field_name, field
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.get_prop_name(),
                "label": cls.get_label(),
                "type": 'Text',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                wiki_dict['content'][cls.get_prop_name()] = ",".join(str(val) for val in value)
            else:
                wiki_dict['content'][cls.get_prop_name()] = str(value)
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            if cls.is_list:
                return {cls.cacao_name: [cls.field_type.wiki_to_id(x) for x in cls.get_field(obj)]}
            else:
                return {cls.cacao_name: cls.field_type.wiki_to_id(cls.get_field(obj))}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            values = data[cls.cacao_name]
            if cls.is_list:
                values = [cls.field_type.id_to_wiki(x) for x in values]
            else:
                values = cls.field_type.id_to_wiki(values)
            cls.set_field(obj, values)
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                    "error",
                    (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                value_list = data.get(cls.cacao_name)
            else:
                value_list = [data.get(cls.cacao_name)]
        
            if not all(isinstance(x, str) and re.match(CACAO_1_1.regex_identifier, x) for x in value_list):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a list of identifiers",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            if cls.identifier_prefix and not all(x.startswith(cls.identifier_prefix) for x in value_list):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must start with '{cls.identifier_prefix}'",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if cls.is_list:
                if not isinstance(value, list):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list")
                value_list = value
            else:
                value_list = [value]
            
            if not all(isinstance(x, str) and re.match(CACAO_1_1.regex_identifier, cls.field_type.wiki_to_id(x)) for x in value_list):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be identifiers")
            if cls.identifier_prefix and not all(x.lower().startswith(cls.field_type.id_to_wiki(cls.identifier_prefix).lower()) for x in value_list):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must start with '{cls.identifier_prefix}'")
            if cls.allowed_values and not all(x in cls.allowed_values for x in value):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be  in {cls.allowed_values}")
        @classmethod
        def validate_field_warnings(cls, obj):
            warnings = []
            if not cls.get_field(obj):
                return warnings
            if cls.contains_keys:
                wiki_names = {x.wiki_page_name for x in obj.playbook.playbook_objects.all()}
                if cls.is_list:
                    value_list = cls.get_field(obj)
                else:
                    value_list = [cls.get_field(obj)]
                for value in value_list:
                    if value not in wiki_names:
                        warnings.append(f"'{value}' not found in playbook objects")
            return warnings
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            if cls.is_list:
                return_dict = {
                    'type': 'List',
                    'label': cls.get_label(),
                    'entries': []
                }
                for x in cls.get_field(obj):
                    if cls.contains_keys and obj_dict and x in obj_dict:
                        return_dict['entries'].append({
                            'type': 'Href',
                            'text': obj_dict[x]['name'],
                            'href': obj_dict[x]['url']
                    })
                    else:
                        return_dict['entries'].append({
                            'type': 'Identifier',
                            'text': str(x),
                        })
                return return_dict
            elif cls.contains_keys and obj_dict and cls.get_field(obj) in obj_dict:
                return {
                    "type": "Href",
                    'label': cls.get_label(),
                    "text": obj_dict[cls.get_field(obj)]['name'],
                    "href": obj_dict[cls.get_field(obj)]['url']
                }
            return {
                "type": "Identifier",
                'label': cls.get_label(),
                "text": str(cls.get_field(obj)),
            }
    class Dictionary_Field(Object_Field):
        field_type = FT.dictionary
        is_list = False
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
                    
            field = cls.prepare_form_field(
                form_fields.CustomJSONField,
            )
            return field_name, field
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.get_prop_name(),
                "label": cls.get_label(),
                "type": 'Text',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            values = [base64.b64decode(x).decode('utf-8') for x in values]
            values = [json.loads(x) for x in values]
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                write_values = [json.dumps(x) for x in value]
                write_values = [base64.b64encode(x.encode('utf-8')).decode('utf-8') for x in write_values]
                write_values = ",".join(write_values)
            else:
                write_values = json.dumps(value)
                write_values = base64.b64encode(write_values.encode('utf-8')).decode('utf-8')
            wiki_dict['content'][cls.get_prop_name()] = write_values
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            return {cls.cacao_name: cls.get_field(obj)}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            cls.set_field(obj, data[cls.cacao_name])
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                    "error",
                    (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                value_list = data.get(cls.cacao_name)
            else:
                value_list = [data.get(cls.cacao_name)]
        
            if not all(isinstance(x, dict) for x in value_list):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a list of dictionaries",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if cls.is_list:
                if not isinstance(value, list):
                    raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list")
                value_list = value
            else:
                value_list = [value]
            
            if not all(isinstance(x, dict) for x in value_list):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must contain dictionaries")
            if cls.allowed_values and not all(x in cls.allowed_values for x in value):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be  in {cls.allowed_values}")
        @classmethod
        def validate_field_warnings(cls, obj):
            return []
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            # TODO: Improve this with hrefs etc.
            return_dict = {
                'type': 'Dict',
                'label': cls.get_label(),
                'content': None
            }
            return_dict['content'] = [{
                    'type': 'String',
                    'label': key,
                    'text': str(value)
                }
                for key, value in cls.get_field(obj).items()
            ]
            return return_dict
        @classmethod
        def initial_fill(cls, obj=None):
            initial = super().initial_fill(obj)
            if initial:
                return json.dumps(initial, indent=4)
            return None
    class Object_List_Field(Object_Field):
        field_type = FT.object_list
        is_list = True
        contains_keys = True
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            
            if hasattr(cls,'filter_choices'):
                choices = [
                    x
                    for x in kwargs.get('playbook_objects', [])
                    if cls.filter_choices(x)
                ]
            else:
                choices = [x for x in kwargs.get('playbook_objects', [])]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.Select2TokenListField,
                    choices=choices,
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.Select2SingleTokenField,
                    choices=choices,
                )
            return field_name, field
        
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.get_prop_name(),
                "label": cls.get_label(),
                "type": 'Page',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            values = [x['fulltext'] for x in values]
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                write_values = ",".join(value)
            else:
                write_values = value
            wiki_dict['content'][cls.get_prop_name()] = write_values
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            
            object_list = cls.get_field(obj)
            query_set = obj.playbook.playbook_objects.filter(wiki_page_name__in=object_list)
            object_list = [query_set.get(wiki_page_name=x) for x in object_list]
            object_list = [x.resolve_subclass() for x in object_list]
            object_list = [x.serialize_object() for x in object_list]
            return {cls.cacao_name: object_list}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            ids = []
            for object_dict in data[cls.cacao_name]:
                if not cls.iterable_type:
                    raise Exception("Object_List_Field must have an iterable_type")
                sub_cls = cls.iterable_type.get_object()
                if hasattr(sub_cls, 'get_subclass'):
                    sub_cls = sub_cls.get_subclass(
                        object_dict.get(sub_cls.Field_Type.cacao_name)
                )
                id = sub_cls.generate_wiki_name()
                new_obj = sub_cls(
                    wiki_page_name=id,
                    wiki_form=sub_cls.cls_form,
                )
                new_obj = new_obj.resolve_subclass()
                new_obj.deserialize_object(object_dict,deserializer)
                deserializer.new_object(new_obj)
                ids += [id]
            cls.set_field(obj, ids)
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                    "error",
                    (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
            if cls.is_list:
                if not isinstance(data.get(cls.cacao_name), list):
                    valid = False
                    errors.append(
                        (f"Field '{cls.cacao_name}' must be a list", 
                        "critical",
                        (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                        )
                    )
                    return valid, errors
                value_list = data.get(cls.cacao_name)
            else:
                value_list = [data.get(cls.cacao_name)]
        
            if not all(isinstance(x, dict) for x in value_list):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a list of dictionaries",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if not isinstance(value, list):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list")
            if not all(isinstance(x, str) for x in value):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of strings")
        @classmethod
        def validate_field_warnings(cls, obj):
            value = cls.get_field(obj, [])
            warnings = []
            wiki_page_names = {x.wiki_page_name for x in obj.playbook.playbook_objects.all()}
            for x in value:
                if x not in wiki_page_names:
                    warnings.append(f"Object '{x}' not found in playbook")
            return warnings
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            return_dict = {
                'type': 'List',
                'label': cls.get_label(),
                'entries': []
            }
            for x in cls.get_field(obj):
                if cls.contains_keys and obj_dict and x in obj_dict:
                    return_dict['entries'].append({
                        'type': 'Href',
                        'text': obj_dict[x]['name'],
                        'href': obj_dict[x]['url']
                })
                else:
                    return_dict['entries'].append({
                        'type': 'String',
                        'text': str(x),
                    })
            return return_dict
    class Object_Dictionary_Field(Object_Field):
        field_type = FT.object_dict
        is_list = True
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
                        
            if hasattr(cls,'filter_choices'):
                choices = [
                    x
                    for x in kwargs.get('playbook_objects', [])
                    if cls.filter_choices(x)
                ]
            else:
                choices = [x for x in kwargs.get('playbook_objects', [])]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.Select2TokenListField,
                    choices=choices,
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.Select2SingleTokenField,
                    choices=choices,
                )
            return field_name, field
        
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.get_prop_name(),
                "label": cls.get_label(),
                "type": 'Page',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            values = [x['fulltext'] for x in values]
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                write_values = ",".join(value)
            else:
                write_values = value
            wiki_dict['content'][cls.get_prop_name()] = write_values
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            
            object_list = cls.get_field(obj)
            query_set = obj.playbook.playbook_objects.filter(wiki_page_name__in=object_list)
            object_list = [query_set.get(wiki_page_name=x) for x in object_list]
            object_list = [x.resolve_subclass() for x in object_list]
            object_list = {
                x.get_cacao_id(): x.serialize_object() 
                for x in object_list
            }
            return {cls.cacao_name: object_list}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            ids = []
            for id_, object_dict in data[cls.cacao_name].items():
                if not cls.iterable_type:
                    raise Exception(f"{cls.get_label()} must have an iterable_type")
                sub_cls = cls.iterable_type.get_object()
                if hasattr(sub_cls, 'get_subclass'):
                    sub_cls = sub_cls.get_subclass(
                        object_dict.get(sub_cls.Field_Type.cacao_name)
                )
                id = sub_cls.generate_wiki_name(name=id_)
                new_obj = sub_cls(
                    wiki_page_name=id,
                    wiki_form=sub_cls.cls_form,
                )
                new_obj = new_obj.resolve_subclass()
                new_obj.deserialize_object(object_dict,deserializer)
                deserializer.new_object(new_obj)
                ids += [id]
            cls.set_field(obj, ids)
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                    "error",
                    (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
                    
            if not all(isinstance(x, dict) for x in data.get(cls.cacao_name).values()):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a list of dictionaries",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if not isinstance(value, list):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list")
            if not all(isinstance(x, str) for x in value):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a list of strings")
        @classmethod
        def validate_field_warnings(cls, obj):
            value = cls.get_field(obj, [])
            warnings = []
            wiki_page_names = {x.wiki_page_name for x in obj.playbook.playbook_objects.all()}
            for x in value:
                if x not in wiki_page_names:
                    warnings.append(f"Object '{x}' not found in playbook")
            return warnings
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            return_dict = {
                'type': 'List',
                'label': cls.get_label(),
                'entries': []
            }
            for x in cls.get_field(obj):
                if cls.contains_keys and obj_dict and x in obj_dict:
                    return_dict['entries'].append({
                        'type': 'Href',
                        'text': obj_dict[x]['name'],
                        'href': obj_dict[x]['url']
                })
                else:
                    return_dict['entries'].append({
                        'type': 'String',
                        'text': str(x),
                    })
            return return_dict
    class Foreign_Object_Field(Object_Field):
        # field_type = FT.object_dict
        is_list = False
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            
            if cls.is_list:
                field = cls.prepare_form_field(
                    form_fields.CustomTokenListField
                )
            else:
                field = cls.prepare_form_field(
                    form_fields.CustomCharField
                )
            return field_name, field
        
        @classmethod
        def get_prop_dict(cls):
            return {
                "name": cls.field_name,
                "prop": cls.get_prop_name(),
                "label": cls.get_label(),
                "type": 'Page',
                "list": cls.is_list,
            }
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            """Reads the field value from a dictionary of wiki data."""
            values = wiki_data.get(cls.get_prop_name(), [])
            values = [x['fulltext'] for x in values]
            if not values:
                return
            cls.set_field(obj, values)
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            if cls.is_list:
                write_values = ",".join(value)
            else:
                write_values = value
            wiki_dict['content'][cls.get_prop_name()] = write_values
            return wiki_dict
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj): # Skip empty fields
                return {}
            
            object_ = cls.get_field(obj)
            object_ = obj.playbook.playbook_objects.get(wiki_page_name=object_)
            object_ = object_.resolve_subclass()
            object_ = object_.serialize_object()
            return {cls.cacao_name: object_}
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            if cls.cacao_name not in data:
                return
            sub_cls = cls.field_type.get_object()
            if hasattr(sub_cls, 'get_subclass'):
                sub_cls = sub_cls.get_subclass(
                    data[cls.cacao_name].get(sub_cls.Field_Type.cacao_name)
            )
            id = sub_cls.generate_wiki_name()
            new_obj = sub_cls(
                wiki_page_name=id,
                wiki_form=sub_cls.cls_form,
            )
            new_obj = new_obj.resolve_subclass()
            new_obj.deserialize_object(data[cls.cacao_name], deserializer)
            deserializer.new_object(new_obj)
            cls.set_field(obj, id)
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of two-tuples with the first element being the error message and the second element being the severity of the error.
            """
            valid, errors = True, []
            if cls.required and not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required", 
                    "error",
                    (json.dumps(data), cls.cacao_name, None)
                    )
                )
            if not data.get(cls.cacao_name): # Allow empty non-required fields
                return valid, errors
                    
            if not isinstance(data.get(cls.cacao_name), dict):
                valid = False
                errors.append(
                    (f"Field '{cls.cacao_name}' must be a dictionary",
                    "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
                return valid, errors
            sub_cls = cls.field_type.get_object()
            if hasattr(sub_cls, 'get_subclass'):
                sub_cls = sub_cls.get_subclass(
                    data[cls.cacao_name].get(sub_cls.Field_Type.cacao_name)
                )
            valid, sub_errors = sub_cls.validate_json(data[cls.cacao_name])
            errors += sub_errors
            return valid, errors
        @classmethod
        def validate_field(cls, value):
            if not isinstance(value, str):
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be a string")
        @classmethod
        def validate_field_warnings(cls, obj):
            value = cls.get_field(obj)
            if not value:
                if cls.required:
                    return [f"Field '{cls.get_label()}' is required"]
                return []
            
            warnings = []
            wiki_page_names = {x.wiki_page_name for x in obj.playbook.playbook_objects.all()}
            if value not in wiki_page_names:
                warnings.append(f"Object '{value}' not found in playbook")
            return warnings
        @classmethod
        def set_field(cls, obj, value):
            cls.validate_field(value)
            obj.content[cls.field_name] = value
        @classmethod
        def get_field(cls, obj, default=None):
            return obj.content.get(cls.field_name, default)
        @classmethod
        def clear_field(cls, obj):
            obj.content.pop(cls.field_name, None)
        @classmethod
        def get_context(cls, obj, obj_dict=None):
            if not cls.get_field(obj):
                return None
            if cls.is_list:
                return_dict = {
                    'type': 'List',
                    'label': cls.get_label(),
                    'entries': []
                }
                for x in cls.get_field(obj):
                    if cls.contains_keys and obj_dict and x in obj_dict:
                        return_dict['entries'].append({
                            'type': 'Href',
                            'text': obj_dict[x]['name'],
                            'href': obj_dict[x]['url']
                    })
                    else:
                        return_dict['entries'].append({
                            'type': 'String',
                            'text': str(x),
                        })
                return return_dict
            else:
                if cls.contains_keys and obj_dict and cls.get_field(obj) in obj_dict:
                    return {
                        'type': 'Href',
                        'label': cls.get_label(),
                        'text': obj_dict[cls.get_field(obj)]['name'],
                        'href': obj_dict[cls.get_field(obj)]['url']
                    }
                return {
                    "type": "String",
                    'label': cls.get_label(),
                    "text": str(cls.get_field(obj)),
                }
    class Abstract_Field_Type(String_Field):
        field_type = FT.string
        required = True
        field_name = "Type"
        cacao_name = "type"
        label = "Type"
        
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            field = cls.prepare_form_field(
                form_fields.CustomChoiceField,
                choices=[(x, x) for x in cls.allowed_values],
            )
            return field_name, field
    class Abstract_Field_CreatedBy(Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Created by"
        cacao_name = "created_by"
        label = "Created By"
        identifier_prefix = "identity--"
        
        @classmethod
        def initial_fill(cls, obj=None):
            initial = super().initial_fill(obj)
            if initial is None:
                return f"identity--{uuid.uuid4()}"
            return initial
    class Abstract_Field_Timestamp(Timestamp_Field):
        field_type= FT.timestamp
        help_text = 'The timestamp data MUST be a valid RFC 3339-formatted timestamp [RFC3339] using the format yyyy-mm-ddThh:mm:ss[.s+]Z where the "s+" represents 1 or more sub-second values.'
        @classmethod
        def initial_fill(cls, obj=None):
            datetm = super().initial_fill(obj)
            if datetm is None:
                if cls.required:
                    return datetime.now(dt_timezone.utc)
                else:
                    return None
            return datetm
    class Abstract_Field_Description(String_Field):
        field_type = FT.string
        required = False
        field_name = "Description"
        cacao_name = "description"
        label = "Description"
        text_area = True
    class Field_BelongsTo(Hidden_Field):
        cacao_name = None
        field_name = "Belongs to"
        prop_name = "Belongs to"
        field_type = FT.command
        
        @classmethod
        def write_to_wiki(cls, obj):
            return super().write_to_wiki(obj, value_=obj.playbook.wiki_page_name)
    
    object_fields = {Field_BelongsTo.__name__:Field_BelongsTo}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wiki_form = self.cls_form
    
    
    @classmethod
    def get_priority(cls):
        return cls.priority
    
    def get_fields_context(self):
        context = []
        obj_dict = {x.wiki_page_name: {
            'url': x.get_absolute_url(),
            'name': x.get_name(),
            } for x in (pbo.resolve_subclass() for pbo in self.playbook.playbook_objects.all())}
        for field in self.object_fields.values():
            field_context = field.get_context(self, obj_dict)
            if field_context:
                context.append(field_context)
        return context
    
    def serialize_object(self):
        """Serializes the playbook object to a dictionary."""
        json_dict = dict()
        for field in self.object_fields.values():
            field_dict = field.serialize_field(self)
            if field_dict:
                json_dict.update(field_dict)
        return json_dict
    
    def deserialize_object(self, data, deserializer):
        """Deserializes the playbook object from a dictionary."""
        for field in self.object_fields.values():
            field.deserialize_field(data, self, deserializer)
    
    @classmethod
    def get_template(cls):
        props = []
        for field in cls.object_fields.values():
            props.append({
                "name": field.field_name,
                'prop': field.get_prop_name(),
                'label': field.get_label(),
                'list': field.field_type.smw_is_list(),
            })
        return {
            'props': props,
            'form_name': cls.cls_form,
        }
    
    @classmethod
    def validate_json(cls, data):
        errors = []
        for field in cls.object_fields.values():
            valid, field_errors = field.validate_field_json(data)
            errors += field_errors
            if not valid:
                return False, errors
        return True, errors
    
    def validate_warnings(self):
        warnings = []
        for field in self.object_fields.values():
            warnings += [f"Field '{field.get_label()}': {x}" for x in field.validate_field_warnings(self)]
        return warnings
    
    def get_context_warnings(self):
        return self.validate_warnings()

    @staticmethod
    def get_class_from_form(wiki_form):
        def all_subclasses(cls):
            return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]
        return {
            cls.cls_form: cls for cls in all_subclasses(CACAO_1_1_PlaybookObject) if cls.cls_form
        }.get(wiki_form, CACAO_1_1_PlaybookObject)
    
    @classmethod
    def get_field_by_name(cls, field_name:str):
        if cls.object_fields_by_name:
            return cls.object_fields_by_name.get(field_name)
        else:
            cls.object_fields_by_name = dict()
            for field in cls.object_fields.values():
                if field.field_name:
                    cls.object_fields_by_name[field.field_name] = field
            return cls.object_fields_by_name.get(field_name)
    
    def add_to_field(self, field_name: str, value: (str|list[str])):
        if field:=self.get_field_by_name(field_name):
            field.add_to_field(self, value)
            return
        raise ValueError(f"Field '{field_name}' not found in object '{self.wiki_page_name}' of type '{self.cls_form}'")
    
    def get_fields(self) -> list['Object_Field']:
        return [x for x in self.object_fields.values() if x.field_name and not x.hidden]
    
    def get_field(self, field_name: str):
        if field:=self.get_field_by_name(field_name):
            field.get_field(self)
            return
        raise ValueError(f"Field '{field_name}' not found in object '{self.wiki_page_name}' of type '{self.cls_form}'")
    
    def clear_field(self, field_name: str):
        if field:=self.get_field_by_name(field_name):
            field.clear_field(self)
            return
        raise ValueError(f"Field '{field_name}' not found in object '{self.wiki_page_name}' of type '{self.cls_form}'")
    
    def set_field(self, field_name: str, value:list):
        if field:=self.get_field_by_name(field_name):
            field.set_field(self, value)
            return
        raise ValueError(f"Field '{field_name}' not found in object '{self.wiki_page_name}' of type '{self.cls_form}'")
    
    def get_cacao_id(self):
        """Inverse of generate_wiki_name. Returns the CACAO ID of the object."""
        raise NotImplementedError(f"get_cacao_id not implemented for class {self.__name__}")    
    
    def read_from_wiki(self, wiki=None):
        """
        This method loads the content of the playbook object from the wiki.
        Does not save object.
        """
        if wiki is None:
            wiki=sasp.wiki_interface.Wiki()
        wiki_dict = wiki.get_page(self)
        for field in self.object_fields.values():
            field.read_from_wiki(wiki_dict, self)
    
    def write_to_wiki(self,wiki=None):
        """
        This method saves the content of the playbook object to the wiki.
        """
        if wiki is None:
            wiki=sasp.wiki_interface.Wiki()
        context = {
            'content' : {}, # field_name: value
            'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            'form_name': self.cls_form
        }
        for field in self.object_fields.values():
            wiki_dict = field.write_to_wiki(self)
            context["content"].update(wiki_dict['content'])
            context["tables"] += (wiki_dict['tables'])
        wiki.set_page(
            self.wiki_page_name,
            context
        )
    
    @classmethod
    def make_relations(cls,obj):
        """
        This method creates semantic relations between the playbook object and other objects.
        """
        new_relations = []
        for field in cls.object_fields.values():
            if field.contains_keys:
                field_value = field.get_field(obj)
                if not field_value:
                    continue
                if not field.is_list:
                    new_relations.append(
                        (
                            obj.wiki_page_name,
                            field.field_name,
                            field_value
                        )
                    )
                else:
                    for obj_ in field_value:
                        new_relations.append(
                            (
                                obj.wiki_page_name,
                                field.field_name,
                                obj_
                            )
                        )
        return new_relations
    
    @classmethod
    def get_cls_label(cls):
        return cls.cls_label if cls.cls_label else cls.cls_form
    # def get_label(self):
    #     return self.get_cls_label()
    
    def get_name(self):
        if self.object_fields.get("Field_Name") and self.object_fields["Field_Name"].get_field(self):
            return self.object_fields["Field_Name"].get_field(self)
        return self.wiki_page_name
    def get_description(self):
        if self.object_fields.get("Field_Description") and self.object_fields["Field_Description"].get_field(self):
            return self.object_fields["Field_Description"].get_field(self)
        return ""
    
    @classmethod
    def get_new_forms(cls) -> list:
        return (x for x in cls.proxyclasses if not x.is_root)
    
    def get_form_fields(self):
        form_fields = dict()
        if self.playbook.pk:
            playbook_objects = [x.resolve_subclass() for x in self.playbook.playbook_objects.all()]
        else:
            playbook_objects = []
        for field in self.object_fields.values():
            if field.hidden:
                continue
            field_name, field_value = field.get_form_field(self, obj=self, playbook_objects=playbook_objects)
            if field_name in form_fields:
                raise ValueError(f"Field '{field_name}' already in form_fields")
            form_fields[field_name] = field_value
            initial = field.initial_fill(self)
            if initial:
                form_fields[field_name].initial = initial
        return form_fields
    
    def get_form_class(self):
        return forms.CACAO_1_1_PlaybookObjectForm
    
    # Do not use this unless you only want to write the object,
    # for updating the wiki page and semantic relations, use the full_save method
    def save(self, *args, **kwargs):
        self.name = self.get_name()
        self.description = self.get_description()
        super().save(*args, **kwargs)
    
    def full_save(self, *args, wiki=None, **kwargs):
        skip_wiki = kwargs.pop("skip_wiki", False)
        skip_relations = kwargs.pop("skip_relations", False)
        skip_register = kwargs.pop("skip_register", False)
        if not skip_wiki and not self.archived:
            self.write_to_wiki(wiki=wiki)
        if not skip_register: # NOTE: Root object pops skip_register before calling this method so it will always be False
            parent = self.playbook.resolve_subclass()
            parent.register_object(self)
        self.save(*args, **kwargs)
        if not skip_relations:
            self.playbook.resolve_subclass().update_relations()
        
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
    
    def remove(self, *args, wiki=None, **kwargs):
        skip_wiki = kwargs.pop("skip_wiki", False)
        skip_deregister = kwargs.pop("skip_deregister", False)
        skip_db_delete = kwargs.pop("skip_db_delete", False)
        if not skip_wiki:
            if wiki is None:
                wiki = sasp.wiki_interface.Wiki()
            wiki.delete_page(self.wiki_page_name)
        if not skip_deregister:
            parent = self.playbook.resolve_subclass()
            parent.deregister_object(self)
        if not skip_db_delete:
            self.delete(*args, **kwargs)
        
class CACAO_1_1_Playbook(CACAO_1_1_PlaybookObject):
    """Contains the content of a CACAO 1.1 Playbook's base object. 
    This is seperate from the object of type 'Playbook' which is the container for all objects in the playbook.
    """
    cls_form = CACAO_1_1.cls_form
    cls_label = "CACAO 1.1 Playbook"
    priority:int = 1000
    
    @classproperty
    def is_root(cls):
        return True
       
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        allowed_values = ["playbook", "playbook-template"]
    class Field_SpecVersion(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Spec version"
        cacao_name = "spec_version"
        label = "Spec Version"
        allowed_values = ["1.1"]
    class Field_ID(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Id"
        cacao_name = "id"
        label = "ID"
        
        @classmethod
        def initial_fill(cls, obj=None):
            if initial:=super().initial_fill(obj):
                return initial
            return f"playbook--{uuid.uuid4()}"
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Name"
        cacao_name = "name"
        
        @classmethod
        def initial_fill(cls, obj=None):
            if initial:=super().initial_fill(obj):
                return initial
            return obj.wiki_page_name
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not data.get(cls.cacao_name):
                errors.append(
                    (f"Field '{cls.cacao_name}' is required for import",
                     "critical",
                     (json.dumps(data), cls.cacao_name, None)
                    )
                )
                return False, errors
            return True, errors
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_PlaybookTypes(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        is_list = True
        required = True
        field_name = "Playbook types"
        cacao_name = "playbook_types"
        label = "Playbook Types"
        allowed_values = [
            "notification",
            "detection",
            "investigation",
            "prevention",
            "mitigation",
            "remediation",
            "attack"
        ]
    class Field_CreatedBy(CACAO_1_1_PlaybookObject.Abstract_Field_CreatedBy):
        pass
    class Field_Created(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        cacao_name = "created"
        field_name = "Created"
        label = "Created"
        required = True
    class Field_Modified(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        cacao_name = "modified"
        field_name = "Modified"
        label = "Modified"
        required = True
    class Field_Revoked(CACAO_1_1_PlaybookObject.Boolean_Field):
        field_type = FT.boolean
        required = False
        field_name = "Revoked"
        cacao_name = "revoked"
        label = "Revoked"
    class Field_ValidFrom(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        cacao_name = "valid_from"
        field_name = "Valid from"
        label = "Valid From"
    class Field_ValidUntil(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        cacao_name = "valid_until"
        field_name = "Valid until"
        label = "Valid Until"
    class Field_DerivedFrom(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        is_list = True
        cacao_name = "derived_from"
        field_name = "Derived from"
        label = "Derived From"
        identifier_prefix = "playbook--"
    class Field_Priority(CACAO_1_1_PlaybookObject.Integer_Field):
        field_type = FT.integer
        required = False
        field_name = "Priority"
        cacao_name = "priority"
        label = "Priority"
        help_text = """A positive integer that represents the priority of this playbook relative to other defined playbooks.\nPriority is a subjective assessment by the producer based on the context in which the playbook can be shared. Marketplaces and sharing organizations MAY define rules on how priority should be assessed and assigned. This property is primarily to allow such usage without requiring the addition of a custom field for such practices.\nIf specified, the value of this property MUST be between 0 and 100.\nWhen left blank this means unspecified. A value of 0 means specifically undefined. Values range from 1, the highest priority, to a value of 100, the lowest."""
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if data.get(cls.cacao_name) and not 0 <= data.get(cls.cacao_name) <= 100:
                errors.append(
                    (f"Field '{cls.cacao_name}' must be an integer between in the range 0-100",
                     "error",
                     (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                    )
                )
            return True, errors
        def validate_field(cls, value):
            if not 0 <= value <= 100:
                raise cls.Exception_Field_Validation(f"Field '{cls.get_label()}' must be an integer between in the range 0-100")
    class Field_Severity(Field_Priority):
        field_name = "Severity"
        cacao_name = "severity"
        label = "Severity"
        help_text = """A positive integer that represents the seriousness of the conditions that this playbook addresses. This is highly dependent on whether it's an incident (in which cases the severity can be mapped to the incident category) or a response to a threat (in which case the severity would likely be mapped to the severity of threat faced or captured by threat intelligence).\nMarketplaces and sharing organizations MAY define additional rules for how this property should be assigned.\nIf specified, the value of this property MUST be between 0 and 100.\nWhen left blank this means unspecified. A value of 0 means specifically undefined. Values range from 1, the lowest severity, to a value of 100, the highest."""
    class Field_Impact(Field_Priority):
        field_name = "Impact"
        cacao_name = "impact"
        label = "Impact"
        help_text = """A positive integer that represents the impact the playbook has on the organization, not what triggered the playbook in the 1st place such as a threat or an incident. For example, a purely investigative playbook that is non-invasive would have a low impact value (1), whereas a playbook that makes firewall changes, IPS changes, moves laptops to quarantine etc., would have a higher impact value. If specified, the value of this property MUST be between 0 and 100.\nWhen left blank this means unspecified. A value of 0 means specifically undefined. Values range from 1, the lowest impact, to a value of 100, the highest."""
    class Field_IndustrySectors(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        is_list = True
        required = False
        field_name = "Industry sectors"
        cacao_name = "industry_sectors"
        label = "Industry Sectors"
        possible_values = [
            'aerospace',
            'aviation',
            'agriculture',
            'automotive',
            'biotechnology',
            'chemical',
            'commercial',
            'consulting',
            'construction',
            'cosmetics',
            'critical-infrastructure',
            'dams',
            'defense',
            'education',
            'emergency-services',
            'energy',
            'non-renewable-energy',
            'renewable-energy',
            'media',
            'financial',
            'food',
            'gambling',
            'government',
            'local-government',
            'national-government',
            'regional-government',
            'public-services',
            'healthcare',
            'information-communications-technology',
            'electronics-hardware',
            'software',
            'telecommunications',
            'legal-services',
            'lodging',
            'manufacturing',
            'maritime',
            'metals',
            'mining',
            'non-profit',
            'humanitarian-aid',
            'human-rights',
            'nuclear',
            'petroleum',
            'pharmaceuticals',
            'research',
            'transportation',
            'logistics-shipping',
            'utilities',
            'video-game',
            'water',
        ]
    class Field_Labels(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        is_list = True
        required = False
        field_name = "Labels"
        cacao_name = "labels"
        label = "Labels"
        possible_values = []
        
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            field_name = cls.field_name
            field = cls.prepare_form_field(
                form_fields.Select2TokenListField,
                choices=[(x, x) for x in cls.possible_values],
            )
            return field_name, field
    class Field_ExternalReferences(CACAO_1_1_PlaybookObject.Object_List_Field):
        field_type = FT.object_list
        iterable_type = FT.external_reference
        required = False
        field_name = "External references"
        cacao_name = "external_references"
        label = "External References"
        contains_keys = True
    class Field_Features(CACAO_1_1_PlaybookObject.Dictionary_Field):
        field_type = FT.dictionary
        required = False
        field_name = "Features"
        cacao_name = "features"
        label = "Features"
        
        @classmethod
        def get_form_field(cls, *args, **kwargs):
            return cls.field_name, cls.prepare_form_field(
                form_fields.CustomFeaturesField,
                choices = zip(
                    [
                        'parallel_processing',
                        'if_logic',
                        'while_logic',
                        'switch_logic',
                        'temporal_logic',
                        'data_markings',
                        'extensions',
                    ],
                    [
                        'Parallel Processing',
                        'If Logic',
                        'While Logic',
                        'Switch Logic',
                        'Temporal Logic',
                        'Data Markings',
                        'Extensions',
                    ]
                ),
                choices_only = True
            )
        
        @classmethod
        def initial_fill(cls, obj=None):
            initial = cls.get_field(obj)
            if initial is None:
                return None
            return [
                key for key in initial if initial[key]
            ]
        
        @classmethod
        def read_from_wiki(cls, wiki_data, obj):
            if wiki_data.get(cls.field_name, []) == []: # Skip empty fields
                return
            dict_ = {
                'parallel_processing': False,
                'if_logic': False,
                'while_logic': False,
                'switch_logic': False,
                'temporal_logic': False,
                'data_markings': False,
                'extensions': False,
            }
            for key in wiki_data[cls.field_name]:
                dict_[key] = True
            cls.set_field(obj, dict_)
        
        @classmethod
        def write_to_wiki(cls, obj):
            value = cls.get_field(obj)
            wiki_dict = {
                'content' : {}, # field_name: value
                'tables' : [], # {'caption': str, 'headers': [str], 'rows': [[str]]}
            }
            if not value:
                return wiki_dict
            wiki_dict['content'][cls.field_name] = ", ".join(x for x in value if value[x])
            return wiki_dict
    class Field_Markings(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        is_list = True
        field_name = "Markings"
        cacao_name = "markings"
        label = "Markings"
        contains_keys = True
    class Field_PlaybookVariables(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        iterable_type = FT.variable
        field_name = "Playbook variables"
        cacao_name = "playbook_variables"
        label = "Playbook Variables"
        contains_keys = True
    class Field_WorkflowStart(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        field_name = "Workflow start"
        cacao_name = "workflow_start"
        label = "Workflow Start"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_StartStep)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_StartStep)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2SingleTokenField,
                choices=choices,
            )
    class Field_WorkflowException(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        field_name = "Workflow exception"
        cacao_name = "workflow_exception"
        label = "Workflow Exception"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2SingleTokenField,
                choices=choices,
            )
    class Field_Workflow(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        iterable_type = FT.workflow_step
        field_name = "Workflow"
        cacao_name = "workflow"
        label = "Workflow"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2TokenListField,
                choices=choices,
            )
    class Field_Targets(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        iterable_type = FT.target
        field_name = "Targets"
        cacao_name = "targets"
        label = "Targets"
        contains_keys = True
        identifier_prefix = "target--"
    class Field_ExtensionDefinitions(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        iterable_type = FT.extension_definition
        field_name = "Extension definitions"
        cacao_name = "extension_definitions"
        label = "Extension Definitions"
        identifier_prefix = "extension-definition--"
        contains_keys = True
    class Field_DataMarkingDefinitions(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        iterable_type = FT.marking_definition
        field_name = "Data marking definitions"
        cacao_name = "data_marking_definitions"
        label = "Data Marking Definitions"
        contains_keys = True
    class Field_Signatures(CACAO_1_1_PlaybookObject.Object_List_Field):
        field_type = FT.object_list
        iterable_type = FT.signature
        field_name = "Signatures"
        cacao_name = "signatures"
        label = "Signatures"
        contains_keys = True
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    def get_absolute_url(self):
        return reverse('playbook-detail', kwargs={'pk': self.playbook.pk})
    def get_delete_url(self):
        return reverse('playbook-delete', kwargs={'pk': self.playbook.pk})
        
    def register_object(self, new_object):
        if isinstance(new_object, CACAO_1_1_ExternalReference):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_ExternalReferences.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_ExternalReferences.add_to_field(self,new_object.wiki_page_name)
        elif isinstance(new_object, CACAO_1_1_Variable):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_PlaybookVariables.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_PlaybookVariables.add_to_field(self,new_object.wiki_page_name)
        elif isinstance(new_object, CACAO_1_1_Step_Object):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_Workflow.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_Workflow.add_to_field(self,new_object.wiki_page_name)
        elif isinstance(new_object, CACAO_1_1_Target):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_Targets.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_Targets.add_to_field(self,new_object.wiki_page_name)
        elif isinstance(new_object, CACAO_1_1_Extension):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_ExtensionDefinitions.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_ExtensionDefinitions.add_to_field(self,new_object.wiki_page_name)
        elif isinstance(new_object, CACAO_1_1_DataMarking):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_DataMarkingDefinitions.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_DataMarkingDefinitions.add_to_field(self,new_object.wiki_page_name)
        elif isinstance(new_object, CACAO_1_1_Signature):
            if new_object.wiki_page_name in CACAO_1_1_Playbook.Field_Signatures.get_field(self, []):
                return
            CACAO_1_1_Playbook.Field_Signatures.add_to_field(self,new_object.wiki_page_name)
    
    def deregister_object(self, new_object):
        if isinstance(new_object, CACAO_1_1_ExternalReference):
            CACAO_1_1_Playbook.Field_ExternalReferences.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_ExternalReferences.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
        elif isinstance(new_object, CACAO_1_1_Variable):
            CACAO_1_1_Playbook.Field_PlaybookVariables.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_PlaybookVariables.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
        elif isinstance(new_object, CACAO_1_1_Step_Object):
            CACAO_1_1_Playbook.Field_Workflow.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_Workflow.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
        elif isinstance(new_object, CACAO_1_1_Target):
            CACAO_1_1_Playbook.Field_Targets.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_Targets.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
        elif isinstance(new_object, CACAO_1_1_Extension):
            CACAO_1_1_Playbook.Field_ExtensionDefinitions.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_ExtensionDefinitions.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
        elif isinstance(new_object, CACAO_1_1_DataMarking):
            CACAO_1_1_Playbook.Field_DataMarkingDefinitions.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_DataMarkingDefinitions.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
        elif isinstance(new_object, CACAO_1_1_Signature):
            CACAO_1_1_Playbook.Field_Signatures.set_field(
                self, 
                [
                    x for x in CACAO_1_1_Playbook.Field_Signatures.get_field(self, [])
                    if x != new_object.wiki_page_name
                ]
            )
    
    # Do not use this unless you only want to write the object,
    # for updating the wiki page and semantic relations, use the full_save method
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
    def full_save(self, *args, **kwargs):
        kwargs.pop("skip_register", False)
        super().full_save(*args,skip_register=True,**kwargs)
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
    
    def get_new_objects(self) -> list:
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return [
            (
                None,
                CACAO_1_1_StartStep.cls_label,
                CACAO_1_1_StartStep.slug,
                self.Field_WorkflowStart.field_name,
            ),
            (
                "Exception Step",
                CACAO_1_1_SingleActionStep.cls_label,
                CACAO_1_1_SingleActionStep.slug,
                self.Field_WorkflowException.field_name,
            ),
            (
                "Exception Step",
                CACAO_1_1_EndStep.cls_label,
                CACAO_1_1_EndStep.slug,
                self.Field_WorkflowException.field_name,
            ),
        ]
    
    def get_confidentiality(self):
        for obj in self.playbook_objects.filter(wiki_form=CACAO_1_1_TlpMarking.cls_form):
            obj = obj.resolve_subclass()
            return CACAO_1_1_TlpMarking.Field_TlpLevel.get_field(obj)
        return "TLP:RED"

    @classmethod
    def get_cls_label(cls):
        """Returns a human readable label for the form of the playbook."""
        return cls.cls_label if cls.cls_label else cls.cls_form
    
    def get_label(self):
        return self.playbook.get_label()
    
    @classmethod
    def generate_wiki_name(cls, *args, name:str=None, **kwargs):
        if name:
            new_name = re.sub(sasp.knowledge.KnowledgeBase.regex_wiki_name_disallowed, "", name)
            new_name = new_name[0].capitalize() + new_name[1:]
            return new_name
        return None

class CACAO_1_1_Step_Object(CACAO_1_1_PlaybookObject):
    priority:int = 100
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        field_type = FT.string
        required = True
        field_name = "Type"
        cacao_name = "type"
        label = "Type"
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Name"
        cacao_name = "name"
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_External_References(CACAO_1_1_PlaybookObject.Object_List_Field):
        field_type = FT.object_list
        required = False
        field_name = "External references"
        cacao_name = "external_references"
        iterable_type = FT.external_reference
        contains_keys = True
    
    class Field_Delay(CACAO_1_1_PlaybookObject.Integer_Field):
        field_type = FT.integer
        required = False
        field_name = "Delay"
        cacao_name = "delay"
        placeholder = "The amount of time in milliseconds that this step SHOULD wait before it starts processing."
        min_value = 0
    class Field_Timeout(CACAO_1_1_PlaybookObject.Integer_Field):
        field_type = FT.integer
        required = False
        field_name = "Timeout"
        cacao_name = "timeout"
        placeholder = "The amount of time in milliseconds that this step MUST wait before considering the step has failed."
    class Field_Step_Variables(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        required = False
        field_name = "Step variables"
        cacao_name = "step_variables"
        label = "Step Variables"
        iterable_type = FT.variable
        contains_keys = True
    class Field_Owner(CACAO_1_1_PlaybookObject.Abstract_Field_CreatedBy):
        required = False
        field_name = "Owner"
        cacao_name = "owner"
        label = "Owner"
    class Field_On_Completion(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = False
        field_name = "On completion"
        cacao_name = "on_completion"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2SingleTokenField,
                choices=choices,
            )
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid,errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if data.get(cls.cacao_name) and (
                data.get(CACAO_1_1_Step_Object.Field_On_Success.cacao_name) or 
                data.get(CACAO_1_1_Step_Object.Field_On_Failure.cacao_name)
            ):
                errors += [
                    ("on_completion and (on_success, on_failure) are mutually exclusive", 
                     "error",
                    (json.dumps(data), cls.cacao_name, None)
                )]
            return True, errors
    class Field_On_Success(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = False
        field_name = "On success"
        cacao_name = "on_success"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2SingleTokenField,
                choices=choices,
            )
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid,errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if data.get(cls.cacao_name) and not data.get(CACAO_1_1_Step_Object.Field_On_Failure.cacao_name):
                errors += [
                    ("on_success requires on_failure", 
                     "error",
                    (json.dumps(data), cls.cacao_name, None)
                )]
            if data.get(cls.cacao_name) and data.get(CACAO_1_1_Step_Object.Field_On_Completion.cacao_name):
                errors += [
                    ("(on_success, on_failure) and on completion are mutually exclusive", 
                     "error",
                    (json.dumps(data), cls.cacao_name, None)
                )]
            return True, errors
    class Field_On_Failure(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = False
        field_name = "On failure"
        cacao_name = "on_failure"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2SingleTokenField,
                choices=choices,
            )
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid,errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if data.get(cls.cacao_name) and not data.get(CACAO_1_1_Step_Object.Field_On_Success.cacao_name):
                errors += [
                    ("on_failure requires on_success", 
                     "error",
                    (json.dumps(data), cls.cacao_name, None)
                )]
            if data.get(cls.cacao_name) and data.get(CACAO_1_1_Step_Object.Field_On_Completion.cacao_name):
                errors += [
                    ("(on_success, on_failure) and on completion are mutually exclusive", 
                     "error",
                    (json.dumps(data), cls.cacao_name, None)
                )]
            return True, errors
    class Field_Step_Extensions(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        required = False
        field_name = "Step extensions"
        cacao_name = "step_extensions"
        label = "Step Extensions"
        iterable_type = FT.extension_definition
        identifier_prefix = "extension-definition--"
        contains_keys = True
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    @classmethod
    def get_new_objects(cls) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return [
            *((
                "On completion",
                step_class.cls_label,
                step_class.slug,
                cls.Field_On_Completion.field_name,
            ) for step_class in [
                CACAO_1_1_EndStep,
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
            *((
                "On success",
                step_class.cls_label,
                step_class.slug,
                cls.Field_On_Success.field_name,
            ) for step_class in [
                CACAO_1_1_EndStep,
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
            *((
                "On failure",
                step_class.cls_label,
                step_class.slug,
                cls.Field_On_Failure.field_name,
            ) for step_class in [
                CACAO_1_1_EndStep,
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
        ]
    
    def get_next_objects(self):
        return {
            "Workflow Step": {
                self.Field_On_Completion.get_label(): [self.Field_On_Completion.get_field(self)] if self.Field_On_Completion.get_field(self) else [],
                self.Field_On_Success.get_label(): [self.Field_On_Success.get_field(self)] if self.Field_On_Success.get_field(self) else [],
                self.Field_On_Failure.get_label(): [self.Field_On_Failure.get_field(self)] if self.Field_On_Failure.get_field(self) else [],
            }
        }
    
    def get_cacao_id(self):
        return FT.identifier.wiki_to_id(self.wiki_page_name)
    
    @classmethod
    def generate_wiki_name(cls, *args, **kwargs):
        if kwargs.get("name"):
            return FT.identifier.id_to_wiki(kwargs["name"])
        return f"Step--{uuid.uuid4()}"
    
    @classmethod
    def get_subclass(cls, type_):
        if type_ == "start":
            return CACAO_1_1_StartStep
        if type_ == "end":
            return CACAO_1_1_EndStep
        if type_ == "single":
            return CACAO_1_1_SingleActionStep
        if type_ == "playbook":
            return CACAO_1_1_PlaybookStep
        if type_ == "parallel":
            return CACAO_1_1_ParallelStep
        if type_ == "if-condition":
            return CACAO_1_1_IfConditionStep
        if type_ == "while-condition":
            return CACAO_1_1_WhileConditionStep
        if type_ == "switch-condition":
            return CACAO_1_1_SwitchConditionStep
        
        raise ValueError(f"Unknown step type '{type_}'")
    
class CACAO_1_1_StartStep(CACAO_1_1_Step_Object):
    cls_form = "Start Step"
    cls_label = "Start Step"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        field_type = FT.string
        required = True
        field_name = "Type"
        cacao_name = "type"
        allowed_values = ["start"]
        
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })

class CACAO_1_1_EndStep(CACAO_1_1_Step_Object):
    cls_form = "End Step"
    cls_label = "End Step"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        field_type = FT.string
        required = True
        field_name = "Type"
        cacao_name = "type"
        allowed_values = ["end"]
    
    @classmethod
    def validate_json(cls, data):
        valid,errors = super().validate_json(data)
        if not valid:
            return False, errors
        if (
            data.get(CACAO_1_1_Step_Object.Field_On_Completion.cacao_name) or
            data.get(CACAO_1_1_Step_Object.Field_On_Success.cacao_name) or
            data.get(CACAO_1_1_Step_Object.Field_On_Failure.cacao_name)):
            errors += [
                ("End steps shouldn't define further steps",
                 "warning", # Warning, because it is technically not forbidden
                    (json.dumps(data), None, None)
                )]
        return True, errors
        
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    def get_next_objects(self):
        return {}
    
    def get_new_objects(cls) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return []

class CACAO_1_1_SingleActionStep(CACAO_1_1_Step_Object):
    cls_form = "Single Action Step"
    cls_label = "Single Action Step"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        allowed_values = ["single"]
    class Field_Commands(CACAO_1_1_Step_Object.Object_List_Field):
        field_type = FT.object_list
        required = False
        field_name = "Commands"
        cacao_name = "commands"
        iterable_type = FT.command
        contains_keys = True
        filter_choices = lambda x: isinstance(x, CACAO_1_1_Command)  # noqa: E731
    class Field_Target(CACAO_1_1_Step_Object.Foreign_Object_Field):
        # WARNING: We inherit from this field in Playbook Step, be careful when changing
        field_type = FT.target
        required = False
        field_name = "Target"
        cacao_name = "target"
        label = "Target"
        contains_keys = True
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not data.get(cls.cacao_name):
                return True, errors
            if data.get(cls.cacao_name) and data.get(CACAO_1_1_SingleActionStep.Field_Target_Ids.cacao_name):
                errors += [
                    ("Target and target ids are mutually exclusive", 
                     "error",
                    (json.dumps(data), cls.cacao_name, None)
                )]
            subclass=CACAO_1_1_Target.get_subclass(data[cls.cacao_name].get("type"))
            if not subclass:
                errors += [
                    ("Target type must be a valid target type", 
                     "critical",
                    (json.dumps(data), cls.cacao_name, json.dumps(data.get(cls.cacao_name)))
                )]
                return False, errors
            
            valid, obj_errors = subclass.validate_json(data[cls.cacao_name])
            errors += obj_errors
            if not valid:
                return False, errors
            return True, errors
    class Field_Target_Ids(CACAO_1_1_Step_Object.Identifier_Field):
        # WARNING: We inherit from this field in Playbook Step, be careful when changing
        field_type = FT.identifier
        is_list = True
        required = False
        field_name = "Target ids"
        cacao_name = "target_ids"
        identifier_prefix = "target--"
        contains_keys = True
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if data.get(cls.cacao_name) and data.get(CACAO_1_1_SingleActionStep.Field_Target.cacao_name):
                errors += [
                    ("Target and target ids are mutually exclusive", 
                     "error",
                     (json.dumps(data), cls.cacao_name, None)
                    )]
            return True, errors
    class Field_In_Args(CACAO_1_1_Step_Object.String_Field):
        # WARNING: We inherit from this field in Playbook Step, be careful when changing
        field_type = FT.string
        is_list = True
        required = False
        field_name = "In args"
        cacao_name = "in_args"
    class Field_Out_Args(CACAO_1_1_Step_Object.String_Field):
        # WARNING: We inherit from this field in Playbook Step, be careful when changing
        field_type = FT.string
        is_list = True
        required = False
        field_name = "Out args"
        cacao_name = "out_args"
    
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
        
    @classmethod
    def validate_json(cls, data):
        valid,errors = super().validate_json(data)
        if not valid:
            return False, errors
        
        if not (
            data.get(CACAO_1_1_Step_Object.Field_On_Completion.cacao_name) or
            data.get(CACAO_1_1_Step_Object.Field_On_Success.cacao_name) or
            data.get(CACAO_1_1_Step_Object.Field_On_Failure.cacao_name)):
            errors += [
                ("Single action step without next steps, all branches must end with an end step",
                 "error",
                (json.dumps(data), None, None)
            )]
        return True, errors
    
    def get_new_objects(self) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return super().get_new_objects() + [
            (
                None, 
             CACAO_1_1_Command.cls_label, 
             CACAO_1_1_Command.slug, 
             self.Field_Commands.field_name,
             ),
        ]
    
class CACAO_1_1_PlaybookStep(CACAO_1_1_Step_Object):
    cls_form = "Playbook Step"
    cls_label = "Playbook Step"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        field_type = FT.string
        required = True
        field_name = "Type"
        cacao_name = "type"
        allowed_values = ["playbook"]
    
    class Field_Playbook_Id(CACAO_1_1_Step_Object.Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Playbook id"
        cacao_name = "playbook_id"
        identifier_prefix = "playbook--"
    
    class Field_Target(CACAO_1_1_SingleActionStep.Field_Target):
        pass # Essentially copied from Single Action Step to avoid code duplication (and for lazy reasons)
    class Field_Target_Ids(CACAO_1_1_SingleActionStep.Field_Target_Ids):
        pass # Essentially copied from Single Action Step to avoid code duplication (and for lazy reasons)
    class Field_In_Args(CACAO_1_1_SingleActionStep.Field_In_Args):
        pass # Essentially copied from Single Action Step to avoid code duplication (and for lazy reasons)
    class Field_Out_Args(CACAO_1_1_SingleActionStep.Field_Out_Args):
        pass # Essentially copied from Single Action Step to avoid code duplication (and for lazy reasons)
    
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
        
    @classmethod
    def validate_json(cls, data):
        valid,errors = super().validate_json(data)
        if not valid:
            return False, errors
        
        if not (
            data.get(CACAO_1_1_Step_Object.Field_On_Completion.cacao_name) or
            data.get(CACAO_1_1_Step_Object.Field_On_Success.cacao_name) or
            data.get(CACAO_1_1_Step_Object.Field_On_Failure.cacao_name)):
            errors += [
                ("Playbook step without next steps, all branches must end with an end step",
                 "error",
                (json.dumps(data), None, None)
            )]
        return True, errors
    
    
class CACAO_1_1_ParallelStep(CACAO_1_1_Step_Object):
    cls_form = "Parallel Step"
    cls_label = "Parallel Step"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        allowed_values = ["parallel"]
    
    class Field_Next_Steps(CACAO_1_1_Step_Object.Identifier_Field):
        field_type = FT.identifier
        is_list = True
        required = True
        field_name = "Next steps"
        cacao_name = "next_steps"
        label = "Next Steps"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2TokenListField,
                choices=choices,
            )
    
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
        
    def get_new_objects(self) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return super().get_new_objects() + [
            *((
                "Next Step", 
                step_type.cls_label,
                step_type.slug,
                self.Field_Next_Steps.field_name,
            ) for step_type in [
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
        ]

    def get_next_objects(self):
        next_objects = super().get_next_objects()
        worflow_steps = next_objects.get("Workflow Step", {})
        worflow_steps[self.Field_Next_Steps.get_label()] = self.Field_Next_Steps.get_field(self) if self.Field_Next_Steps.get_field(self) else []
        return next_objects
    
    
class CACAO_1_1_IfConditionStep(CACAO_1_1_Step_Object):
    cls_form = "If Condition Step"
    cls_label = "If Condition Step"
    class Meta:
        proxy = True
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        allowed_values = ["if-condition"]
    class Field_Condition(CACAO_1_1_Step_Object.String_Field):
        field_type = FT.string
        required = True
        field_name = "Condition"
        cacao_name = "condition"
        label = "Condition"
    class Field_On_True(CACAO_1_1_Step_Object.Identifier_Field):
        field_type = FT.identifier
        is_list = True
        required = True
        field_name = "On true"
        cacao_name = "on_true"
        label = "On True"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2TokenListField,
                choices=choices,
            )
    class Field_On_False(CACAO_1_1_Step_Object.Identifier_Field):
        field_type = FT.identifier
        is_list = True
        required = True
        field_name = "On false"
        cacao_name = "on_false"
        label = "On False"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2TokenListField,
                choices=choices,
            )
        
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    def get_new_objects(self) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return super().get_new_objects() + [
            *((
                "On true",
                step_type.cls_label,
                step_type.slug,
                self.Field_On_True.field_name,
            ) for step_type in [
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
            *((
                "On false",
                step_type.cls_label,
                step_type.slug,
                self.Field_On_False.field_name,
            ) for step_type in [
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
        ]
    
    def get_next_objects(self):
        next_objects = super().get_next_objects()
        workflow_steps = next_objects.get("Workflow Step", {})
        workflow_steps[self.Field_On_True.get_label()] = self.Field_On_True.get_field(self) if self.Field_On_True.get_field(self) else []
        workflow_steps[self.Field_On_False.get_label()] = self.Field_On_False.get_field(self) if self.Field_On_False.get_field(self) else []
        return next_objects
    
    
class CACAO_1_1_WhileConditionStep(CACAO_1_1_Step_Object):
    cls_form = "While Condition Step"
    cls_label = "While Condition Step"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        allowed_values = ["while-condition"]
    class Field_Condition(CACAO_1_1_IfConditionStep.Field_Condition):
        pass
    class Field_On_True(CACAO_1_1_IfConditionStep.Field_On_True):
        pass
    class Field_On_False(CACAO_1_1_PlaybookStep.Identifier_Field):
        field_type = FT.identifier
        required = True # This is dumb, but in the spec it is required. I think they fixed that in a later version
        field_name = "On false"
        cacao_name = "on_false"
        label = "On False"
        identifier_prefix = "step--"
        contains_keys = True
        
        @classmethod
        def get_form_field(cls, *args, obj=None, **kwargs):
            if 'playbook_objects' in kwargs:
                choices = [x for x in kwargs['playbook_objects'] if isinstance(x, CACAO_1_1_Step_Object)]
            else:
                choices = [x.resolve_subclass() for x in obj.playbook.playbook_objects.all()]
                choices = [x for x in choices if isinstance(x, CACAO_1_1_Step_Object)]
            choices = [(x.wiki_page_name, x.get_name()) for x in choices]
            return cls.field_name, cls.prepare_form_field(
                form_fields.Select2SingleTokenField,
                choices=choices,
            )
        
    def get_new_objects(self) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return super().get_new_objects() + [
            *((
                "On true",
                step_type.cls_label,
                step_type.slug,
                self.Field_On_True.field_name,
            ) for step_type in [
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
            *((
                "On false",
                step_type.cls_label,
                step_type.slug,
                self.Field_On_False.field_name,
            ) for step_type in [
                CACAO_1_1_EndStep,
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
        ]
    
    def get_next_objects(self):
        next_objects = super().get_next_objects()
        workflow_steps = next_objects.get("Workflow Step", {})
        workflow_steps[self.Field_On_True.get_label()] = self.Field_On_True.get_field(self) if self.Field_On_True.get_field(self) else []
        workflow_steps[self.Field_On_False.get_label()] = self.Field_On_False.get_field(self) if self.Field_On_False.get_field(self) else []
        return next_objects
    
    
class CACAO_1_1_SwitchConditionStep(CACAO_1_1_Step_Object):
    cls_form = "Switch Condition Step"
    cls_label = "Switch Condition Step"
    # NOTE: This is the worst class in the entire spec. Of note:
    # - 'Switch' is supposed to be the name of a variable, but our variables are objects,
    #   so it would be neater to have a reference to a variable object.
    # - 'cases' is a dictionary with strings as keys and lists of identifiers as values.
    #   This just doesn't work with our current model, so we have to do some weird stuff.
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Step_Object.Field_Type):
        allowed_values = ["switch-condition"]
    class Field_Switch(CACAO_1_1_Step_Object.String_Field):
        field_type = FT.string
        required = True
        field_name = "Switch"
        cacao_name = "switch"
        label = "Switch"
    class Field_Cases(CACAO_1_1_PlaybookStep.Dictionary_Field):
        field_type = FT.dictionary
        required = True
        field_name = "Cases"
        cacao_name = "cases"
        label = "Cases"
        iterable_type = FT.string
        
        @classmethod
        def serialize_field(cls, obj, *args, **kwargs):
            """Serializes the field to a dictionary."""
            if not cls.get_field(obj):
                return {}
            return {cls.cacao_name: {
                case: [FT.identifier.wiki_to_id(x) for x in id_list]
                for case,id_list in cls.get_field(obj).items()
            }}
        
        @classmethod
        def deserialize_field(cls, data, obj, deserializer, *args, **kwargs):
            if not data.get(cls.cacao_name):
                return
            case_table = {}
            for case, id_list in data[cls.cacao_name].items():
                case_table[case] = [FT.identifier.id_to_wiki(x) for x in id_list]
            cls.set_field(obj, case_table)
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            errors = []
            if not data.get(cls.cacao_name):
                errors += [("Cases must be defined", "error", (json.dumps(data), cls.cacao_name, None))]
                return True, errors
            if not isinstance(data[cls.cacao_name], dict):
                errors += [("Cases must be a dictionary", "critical", (json.dumps(data), cls.cacao_name, data[cls.cacao_name]))]
                return False, errors
            for case, id_list in data[cls.cacao_name].items():
                if not isinstance(id_list, list):
                    errors += [(f"Case {case} must be a list", "critical", (json.dumps(data), cls.cacao_name, data[cls.cacao_name]))]
                    return False, errors
                for id in id_list:
                    if not isinstance(id, str):
                        errors += [(f"Case {case} must be a list of strings", "critical", (json.dumps(data), cls.cacao_name, data[cls.cacao_name]))]
                        return False, errors
                    if not re.match(CACAO_1_1.regex_identifier, id):
                        errors += [(f"Case {case} must be a list of identifiers", "error", (json.dumps(data), cls.cacao_name, f"{case}:{id}"))]
            return True, errors
            
        @classmethod
        def write_to_wiki(cls, obj):
            """Returns a dictionary for the field to be written to the wiki."""
            value = cls.get_field(obj)
            if not value:
                return {}
            wiki_dict = super().write_to_wiki(obj)
            case_table = {
                'caption': 'Cases',
                'headers': ['Case', 'Steps'],
                'rows': [
                    [case, ",".join(id_list)]
                    for case, id_list in value.items()
                ]
            }
            wiki_dict['tables'].append(case_table)
            return wiki_dict
        
    
    object_fields = CACAO_1_1_Step_Object.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    def get_new_objects(self) -> list:        
        # Tuples of (Heading|None, Label, Object Form, (Field Reference,)|None, ObjectID)
        return super().get_new_objects() + [
            *((
                "New Case",
                step_type.cls_label,
                step_type.slug,
                self.Field_Cases.field_name,
            ) for step_type in [
                CACAO_1_1_SingleActionStep,
                CACAO_1_1_PlaybookStep,
                CACAO_1_1_ParallelStep,
                CACAO_1_1_IfConditionStep,
                CACAO_1_1_WhileConditionStep,
                CACAO_1_1_SwitchConditionStep,
            ]),
        ]
    
    def add_to_field(self, field_name, value):
        if field_name == CACAO_1_1_SwitchConditionStep.Field_Cases.field_name:
            i=1
            case_table = self.content.get('case_table', {})
            while f"Condition{i}" in case_table:
                i += 1
            condition_placeholder = f"Condition{i}"
            CACAO_1_1_SwitchConditionStep.Field_Cases.add_to_field(self, (condition_placeholder, value))
        else:
            super().add_to_field(field_name, value)
    
    def get_next_objects(self):
        next_objects = super().get_next_objects()
        workflow_steps = next_objects.get("Workflow Step", {})
        cases = []
        if not self.Field_Cases.get_field(self):
            for case_list in self.Field_Cases.get_field(self).values():
                for case in case_list:
                    cases.append(case)
        
        workflow_steps[self.Field_Cases.get_label()] = cases
        return next_objects
    
    
class CACAO_1_1_Command(CACAO_1_1_PlaybookObject):
    cls_form = "Command"
    cls_label = "Command"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        allowed_values = [
            "manual",
            "http-api",
            "ssh",
            "bash",
            "openc2-json",
            "attack-cmd",
            "sigma",
            "jupyter",
            "kestrel"
        ]
    class Field_Command(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Command"
        cacao_name = "command"
        label = "Command"
    class Field_Command_B64(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Command b64"
        cacao_name = "command_b64"
        label = "Command b64"
    class Field_Version(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Version"
        cacao_name = "version"
        label = "Version"
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and
        cls.__name__.startswith("Field_")
    })
    
    @classmethod
    def generate_wiki_name(cls, *args, name:str=None, **kwargs):
        if name:
            return f"Command--{uuid.uuid4()}--{re.sub(sasp.knowledge.KnowledgeBase.regex_wiki_name_allowed, '', name)}"
        else:
            # NOTE: Commands don't have a name field, they are only identified by the key in
            # the variable dictionary, which really doesn't work for us.
            # Current plan is to change the new object view to allow the user to enter a name
            return f"Command--{uuid.uuid4()}--{timezone.now().strftime('%Y%m%d%H%M%S')}"
        

class CACAO_1_1_Target(CACAO_1_1_PlaybookObject):
    class Meta:
        proxy = True
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        pass
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Name"
        cacao_name = "name"
        label = "Name"
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_Target_Extensions(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        required = False
        field_name = "Target extensions"
        cacao_name = "target_extensions"
        label = "Target Extensions"
        iterable_type = FT.extension_definition
        identifier_prefix = "extension-defintion--"
        contains_keys = True
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    def get_subclass(type_name: str):        
        if type_name == "individual":
            return CACAO_1_1_IndividualTarget
        elif type_name == "group":
            return CACAO_1_1_GroupTarget
        elif type_name == "organization":
            return CACAO_1_1_GroupTarget
        elif type_name == "location":
            return CACAO_1_1_LocationTarget
        elif type_name == "sector":
            return CACAO_1_1_SecurityInfrastructureCategoryTarget
        elif type_name == "http-api":
            return CACAO_1_1_HttpApiTarget
        elif type_name == "ssh":
            return CACAO_1_1_SshCliTarget
        elif type_name == "security-infrastructure-category":
            return CACAO_1_1_SecurityInfrastructureCategoryTarget
        elif type_name == "net-address":
            return CACAO_1_1_GeneralNetworkAddressTarget
        elif type_name == "kali":
            return CACAO_1_1_KaliLinuxTarget
        elif type_name == "attacker":
            return CACAO_1_1_AttackerTarget
        elif type_name == "attack-agent":
            return CACAO_1_1_AttackAgentTarget
        elif type_name == "attack-group":
            return CACAO_1_1_AttackGroupTarget
        raise ValueError(f"Unknown target type: {type_name}")
    
    @classmethod
    def generate_wiki_name(cls, *args, **kwargs):
        return f"Target--{uuid.uuid4()}"
    def get_cacao_id(self):
        return FT.identifier.wiki_to_id(self.wiki_name)
class CACAO_1_1_IndividualTarget(CACAO_1_1_Target):
    cls_form = "Individual Target"
    cls_label = "Individual Target"
    class Meta:
        proxy = True
        
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["individual"]
    class Field_Contact(CACAO_1_1_PlaybookObject.Foreign_Object_Field):
        field_type = FT.contact
        required = False
        field_name = "Contact"
        cacao_name = "contact"
        label = "Contact"
        contains_keys = True
    class Field_Location(CACAO_1_1_PlaybookObject.Foreign_Object_Field):
        field_type = FT.civic_location
        required = False
        field_name = "Location"
        cacao_name = "location"
        label = "Location"
        contains_keys = True
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_GroupTarget(CACAO_1_1_Target):
    cls_form = "Group Target"
    cls_label = "Group Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["group"]
    class Field_Contact(CACAO_1_1_IndividualTarget.Field_Contact):
        pass
    class Field_Location(CACAO_1_1_IndividualTarget.Field_Location):
        pass
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_OrganizationTarget(CACAO_1_1_Target):
    cls_form = "Organization Target"
    cls_label = "Organization Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["organization"]
    class Field_Contact(CACAO_1_1_IndividualTarget.Field_Contact):
        pass
    class Field_Location(CACAO_1_1_IndividualTarget.Field_Location):
        pass
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_LocationTarget(CACAO_1_1_Target):
    cls_form = "Location Target"
    cls_label = "Location Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["location"]
    class Field_Location(CACAO_1_1_IndividualTarget.Field_Location):
        pass
    class Field_Gps(CACAO_1_1_PlaybookObject.Foreign_Object_Field):
        field_type = FT.gps_location
        required = False
        field_name = "Gps"
        cacao_name = "gps"
        label = "Gps"
    class Field_Logical(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        is_list = True
        required = False
        field_name = "Logical"
        cacao_name = "logical"
        label = "Logical"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_SectorTarget(CACAO_1_1_Target):
    cls_form = "Sector Target"
    cls_label = "Sector Target"
    class Meta:
        proxy = True
        
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["sector"]
    class Field_Location(CACAO_1_1_Target.Object_List_Field):
        field_type = FT.civic_location
        required = False
        field_name = "Location"
        cacao_name = "location"
        label = "Location"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_HttpApiTarget(CACAO_1_1_Target):
    cls_form = "HTTP API Target"
    cls_label = "HTTP API Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["http-api"]
    class Field_Http_Url(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Http url"
        cacao_name = "http_url"
        label = "Http Url"
    class Field_Http_Auth_Type(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Http auth type"
        cacao_name = "http_auth_type"
        label = "Http Auth Type"
    class Field_User_Id(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "User id"
        cacao_name = "user_id"
        label = "User Id"
    class Field_Password(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Password"
        cacao_name = "password"
        label = "Password"
    class Field_Token(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Token"
        cacao_name = "token"
        label = "Token"
    class Field_Oauth_Header(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Oauth header"
        cacao_name = "oauth_header"
        label = "Oauth Header"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_SshCliTarget(CACAO_1_1_Target):
    cls_form = "SSH CLI Target"
    cls_label = "SSH CLI Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["ssh"]
    class Field_Address(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Address"
        cacao_name = "address"
        label = "Address"
    class Field_Port(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Port"
        cacao_name = "port"
        label = "Port"
    class Field_Username(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Username"
        cacao_name = "username"
        label = "Username"
    class Field_Password(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Password"
        cacao_name = "password"
        label = "Password"
    class Field_Private_Key(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Private key"
        cacao_name = "private_key"
        label = "Private Key"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_SecurityInfrastructureCategoryTarget(CACAO_1_1_Target):
    cls_form = "Security Infrastructure Category Target"
    cls_label = "Security Infrastructure Category Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["security-infrastructure-category"]
    class Field_Category(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        is_list = True
        required = True
        field_name = "Category"
        prop_name = "Prop Category"
        cacao_name = "category"
        label = "Category"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_GeneralNetworkAddressTarget(CACAO_1_1_Target):
    cls_form = "General Network Address Target"
    cls_label = "General Network Address Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["net-address"]
    class Field_Address(CACAO_1_1_PlaybookObject.Dictionary_Field):
        field_type = FT.dictionary
        required = True
        field_name = "Address"
        cacao_name = "address"
        label = "Address"
        iterable_type = FT.string
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not all(isinstance(x, str) for x in data[cls.cacao_name].values()):
                errors += [
                    ("Address must be a dictionary of strings", "critical", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
                return False, errors
            if not all(key in {'ipv4', 'ipv6', 'l2mac', 'vlan', 'url'} for key in data[cls.cacao_name]):
                errors += [
                    ("Address must be a dictionary with keys 'ipv4', 'ipv6', 'l2mac', 'vlan', 'url'", "critical", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
                return False, errors
            return True, errors
        
    class Field_Username(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Username"
        cacao_name = "username"
        label = "Username"
    class Field_Password(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Password"
        cacao_name = "password"
        label = "Password"
    class Field_Private_Key(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Private key"
        cacao_name = "private_key"
        label = "Private Key"
    class Field_Category(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Category"
        prop_name = "Prop Category"
        cacao_name = "category"
        label = "Category"
        possible_values = [
            'endpoint',
            'handset',
            'router',
            'firewall',
            'ids',
            'ips',
            'aaa',
            'os-windows',
            'os-linux',
            'os-mac',
            'switch',
            'wireless',
            'desktop',
            'server',
            'content-gateway',
            'analytics',
            'siem',
            'tip',
            'ticketing'
        ]
    class Field_Location(CACAO_1_1_PlaybookObject.Foreign_Object_Field):
        field_type = FT.civic_location
        required = False
        field_name = "Location"
        cacao_name = "location"
        label = "Location"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_AttackerTarget(CACAO_1_1_Target):
    cls_form = "Attacker Target"
    cls_label = "Attacker Target"
    class Meta:
        proxy = True
        
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["attacker"]
    class Field_Executor(CACAO_1_1_PlaybookObject.Foreign_Object_Field):
        field_type = FT.target
        required = True
        field_name = "Executor"
        cacao_name = "executor"
        label = "Executor"
    class Field_Executor_Type(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Executor type"
        cacao_name = "executor-type"
        label = "Executor Type"
        allowed_values = [
            'kali',
            'caldera',
            'redcanary-atomicred'
            'jupyter',
            'kestrel'
        ]
    class Field_Subject(CACAO_1_1_PlaybookObject.Foreign_Object_Field):
        field_type = FT.target
        required = True
        field_name = "Subject"
        cacao_name = "subject"
        label = "Subject"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_AttackAgentTarget(CACAO_1_1_Target):
    cls_form = "Attack Agent Target"
    cls_label = "Attack Agent Target"
    class Meta:
        proxy = True
        
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["attack-agent"]
    class Field_Address(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Address"
        cacao_name = "address"
        label = "Address"
    class Field_Agent_Type(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Agent type"
        cacao_name = "agent-type"
        label = "Agent Type"
        allowed_values = [
            'sandcat',
            'manx',
            'ragdoll',
        ]
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_AttackGroupTarget(CACAO_1_1_Target):
    cls_form = "Attack Group Target"
    cls_label = "Attack Group Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["attack-group"]
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Name"
        cacao_name = "name"
        label = "Name"
    
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_KaliLinuxTarget(CACAO_1_1_Target):
    cls_form = "Kali Linux Target"
    cls_label = "Kali Linux Target"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_Target.Field_Type):
        allowed_values = ["kali"]
    class Field_Address(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Address"
        cacao_name = "address"
        label = "Address"
    class Field_Port(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Port"
        cacao_name = "port"
        label = "Port"
    class Field_Username(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Username"
        cacao_name = "username"
        label = "Username"
    class Field_Password(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Password"
        cacao_name = "password"
        label = "Password"
    class Field_Private_Key(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Private key"
        cacao_name = "private_key"
        label = "Private Key"
        
    object_fields = CACAO_1_1_Target.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_Extension(CACAO_1_1_PlaybookObject):
    cls_form = "Extension"
    cls_label = "Extension"
    class Meta:
        proxy = True
        
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        allowed_values = ["extension-definition"]
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Name"
        cacao_name = "name"
        label = "Name"
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_CreatedBy(CACAO_1_1_PlaybookObject.Abstract_Field_CreatedBy):
        pass
    class Field_Schema(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Schema"
        cacao_name = "schema"
        label = "Schema"
    class Field_Version(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Version"
        cacao_name = "version"
        label = "Version"
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    @classmethod
    def generate_wiki_name(cls, *args, name:str=None, **kwargs):
        if name:
            return FT.identifier.id_to_wiki_name(name)
        return f"Extension-Definition--{uuid.uuid4()}"
    def get_cacao_id(self):
        return FT.identifier.wiki_name_to_id(self.wiki_page_name)
    
class CACAO_1_1_DataMarking(CACAO_1_1_PlaybookObject):
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        pass
    class Field_SpecVersion(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Spec version"
        cacao_name = "spec_version"
        label = "Spec Version"
    class Field_Id(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Id"
        cacao_name = "id"
        label = "Id"
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Name"
        cacao_name = "name"
        label = "Name"
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_CreatedBy(CACAO_1_1_PlaybookObject.Abstract_Field_CreatedBy):
        pass
    class Field_Created(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = True
        field_name = "Created"
        cacao_name = "created"
        label = "Created"
    class Field_Modified(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = True
        field_name = "Modified"
        cacao_name = "modified"
        label = "Modified"
    class Field_Revoked(CACAO_1_1_PlaybookObject.Boolean_Field):
        field_type = FT.boolean
        required = False
        field_name = "Revoked"
        cacao_name = "revoked"
        label = "Revoked"
    class Field_ValidFrom(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = False
        field_name = "Valid from"
        cacao_name = "valid_from"
        label = "Valid From"
    class Field_ValidUntil(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = False
        field_name = "Valid until"
        cacao_name = "valid_until"
        label = "Valid Until"
    class Field_Labels(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        is_list = True
        required = False
        field_name = "Labels"
        cacao_name = "labels"
        label = "Labels"
    class Field_ExternalReferences(CACAO_1_1_PlaybookObject.Object_List_Field):
        field_type = FT.object_list
        required = False
        field_name = "External references"
        cacao_name = "external_references"
        label = "External References"
        iterable_type = FT.external_reference
        contains_keys = True
    class Field_MarkingExtensions(CACAO_1_1_PlaybookObject.Object_Dictionary_Field):
        field_type = FT.object_dict
        required = False
        field_name = "Marking extensions"
        cacao_name = "marking_extensions"
        label = "Marking Extensions"
        iterable_type = FT.extension_definition
        identifier_prefix = "extension-definition--"
        contains_keys = True
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not all(isinstance(x, str) for x in data[cls.cacao_name].values()):
                errors += [
                    ("Marking extensions must be a dictionary of JSON strings", "critical", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
                return False, errors
            return True, errors
        
        
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    @classmethod
    def get_subclass(cls, type_):
        if type_ == "marking-statement":
            return CACAO_1_1_StatementMarking
        if type_ == "marking-tlp":
            return CACAO_1_1_TlpMarking
        if type_ == "marking-iep":
            return CACAO_1_1_IepMarking
        raise ValueError(f"Unknown type {type_}")
    
class CACAO_1_1_StatementMarking(CACAO_1_1_DataMarking):
    cls_form = "Statement Marking"
    cls_label = "Statement Marking"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_DataMarking.Field_Type):
        allowed_values = ["marking-statement"]
    class Field_Id(CACAO_1_1_DataMarking.Field_Id):
        identifier_prefix = "marking-statement--"
    class Field_Statement(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Statement"
        cacao_name = "statement"
        label = "Statement"
    
    object_fields = CACAO_1_1_DataMarking.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_TlpMarking(CACAO_1_1_DataMarking):
    cls_form = "TLP Marking"
    cls_label = "TLP Marking"
    class Meta:
        proxy = True
        
    class Field_Type(CACAO_1_1_DataMarking.Field_Type):
        allowed_values = ["marking-tlp"]
    class Field_Id(CACAO_1_1_DataMarking.Field_Id):
        identifier_prefix = "marking-tlp--"
    class Field_TlpLevel(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Tlp level"
        cacao_name = "tlp_level"
        label = "Tlp Level"
        allowed_values = [
            'TLP:RED',
            'TLP:AMBER',
            'TLP:GREEN',
            'TLP:WHITE'
        ]
    
    object_fields = CACAO_1_1_DataMarking.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_IepMarking(CACAO_1_1_DataMarking):
    cls_form = "IEP Marking"
    cls_label = "IEP Marking"
    class Meta:
        proxy = True
    
    # type;Y;string
    # name;Y;string
    # tlp_level;;string
    # description;;string
    # iep_version;;string
    # start_date;;timestamp
    # end_date;;timestamp
    # encrypt_in_transit;;string
    # permitted_actions;;string
    # attribution;;string
    # unmodified_resale;;string
    class Field_Type(CACAO_1_1_DataMarking.Field_Type):
        allowed_values = ["marking-iep"]
    class Field_Id(CACAO_1_1_DataMarking.Field_Id):
        identifier_prefix = "marking-iep--"
    class Field_Name(CACAO_1_1_DataMarking.Field_Name):
        required = True
    class Field_TlpLevel(CACAO_1_1_TlpMarking.Field_TlpLevel):
        field_type = FT.string
        required = False
        field_name = "Tlp level"
        cacao_name = "tlp_level"
        label = "Tlp Level"
    class Field_Description(CACAO_1_1_DataMarking.Field_Description):
        required = False
    class Field_IepVersion(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Iep version"
        cacao_name = "iep_version"
        label = "IEP Version"
    class Field_StartDate(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = False
        field_name = "Start date"
        cacao_name = "start_date"
        label = "Start Date"
    class Field_EndDate(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = False
        field_name = "End date"
        cacao_name = "end_date"
        label = "End Date"
    class Field_EncryptInTransit(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Encrypt in transit"
        cacao_name = "encrypt_in_transit"
        label = "Encrypt in Transit"
    class Field_PermittedActions(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Permitted actions"
        cacao_name = "permitted_actions"
        label = "Permitted Actions"
    class Field_Attribution(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Attribution"
        cacao_name = "attribution"
        label = "Attribution"
    class Field_UnmodifiedResale(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Unmodified resale"
        cacao_name = "unmodified_resale"
        label = "Unmodified Resale"
    
    object_fields = CACAO_1_1_DataMarking.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    
class CACAO_1_1_CivicLocation(CACAO_1_1_PlaybookObject):
    cls_form = "Civic Location"
    cls_label = "Civic Location"
    class Meta:
        proxy = True
    
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_BuildingDetails(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Building details"
        cacao_name = "building_details"
        label = "Building Details"
    class Field_NetworkDetails(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Network details"
        cacao_name = "network_details"
        label = "Network Details"
    class Field_Region(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Region"
        cacao_name = "region"
        label = "Region"
        allowed_values = [
            "africa",
            "eastern-africa",
            "middle-africa",
            "northern-africa",
            "southern-africa",
            "western-africa",
            "americas",
            "caribbean",
            "central-america",
            "latin-america-caribbean",
            "northern-america",
            "south-america",
            "asia",
            "central-asia",
            "eastern-asia",
            "southern-asia",
            "south-eastern-asia",
            "western-asia",
            "europe",
            "eastern-europe",
            "northern-europe",
            "southern-europe",
            "western-europe",
            "oceania",
            "antarctica",
            "australia-new-zealand",
            "melanesia",
            "micronesia",
            "polynesia",
        ]
    class Field_Country(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Country"
        cacao_name = "country"
        label = "Country"
    class Field_AdministrativeArea(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Administrative area"
        cacao_name = "administrative_area"
        label = "Administrative Area"
    class Field_City(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "City"
        cacao_name = "city"
        label = "City"
    class Field_StreetAddress(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Street address"
        cacao_name = "street_address"
        label = "Street Address"
    class Field_PostalCode(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Postal code"
        cacao_name = "postal_code"
        label = "Postal Code"
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    @classmethod
    def generate_wiki_name(cls, *args, **kwargs):
        return f"Civic-Location--{uuid.uuid4()}"

class CACAO_1_1_ContactInformation(CACAO_1_1_PlaybookObject):
    cls_form = "Contact Information"
    cls_label = "Contact Information"
    class Meta:
        proxy = True
    
    class Field_Email(CACAO_1_1_PlaybookObject.Dictionary_Field):
        field_type = FT.dictionary
        required = False
        field_name = "Email"
        cacao_name = "email"
        label = "Email"
        iterable_type = FT.string
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not all(isinstance(x, str) for x in data[cls.cacao_name].values()):
                errors += [
                    ("Email must be a dictionary of strings", "critical", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
                return False, errors
            return True, errors
        
    class Field_Phone(CACAO_1_1_PlaybookObject.Dictionary_Field):
        field_type = FT.dictionary
        required = False
        field_name = "Phone"
        cacao_name = "phone"
        label = "Phone"
        iterable_type = FT.string
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not all(isinstance(x, str) for x in data[cls.cacao_name].values()):
                errors += [
                    ("Phone must be a dictionary of strings", "critical", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
                return False, errors
            return True, errors
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    @classmethod
    def generate_wiki_name(cls, *args, **kwargs):
        return f"Contact--{uuid.uuid4()}"
    
class CACAO_1_1_ExternalReference(CACAO_1_1_PlaybookObject):
    cls_form = "External Reference"
    cls_label = "External Reference"
    class Meta:
        proxy = True
    
    class Field_Name(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Name"
        cacao_name = "name"
        label = "Name"
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_Source(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Source"
        cacao_name = "source"
        label = "Source"
    class Field_Url(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Url"
        cacao_name = "url"
        label = "Url"
    class Field_ExternalId(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "External id"
        cacao_name = "external_id"
        label = "External Id"
    class Field_ReferenceId(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Reference id"
        cacao_name = "reference_id"
        label = "Reference Id"
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    @staticmethod
    def generate_wiki_name(*args, **kwargs):
        return f"External-Reference--{uuid.uuid4()}"
    
    
class CACAO_1_1_GpsLocation(CACAO_1_1_PlaybookObject):
    cls_form = "GPS Location"
    cls_label = "GPS Location"
    class Meta:
        proxy = True
    
    class Field_Latitude(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Latitude"
        cacao_name = "latitude"
        label = "Latitude"
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not data.get(cls.cacao_name):
                return True, errors
            try:
                value = float(data[cls.cacao_name])
                if not (-90 < value <= 90):
                    errors += [
                        ("Latitude must be between -90 and 90", "error", 
                         (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
            except ValueError:
                errors += [
                    ("Latitude must be a float", "error", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
            if not data.get(CACAO_1_1_GpsLocation.Field_Longitude.cacao_name):
                errors += [
                    ("Longitude is required if Latitude is provided", "error", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
            
                
            
    class Field_Longitude(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Longitude"
        cacao_name = "longitude"
        label = "Longitude"
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not data.get(cls.cacao_name):
                return True, errors
            try:
                value = float(data[cls.cacao_name])
                if not (-180 < value <= 180):
                    errors += [
                        ("Longitude must be between -90 and 90", "error", 
                         (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
            except ValueError:
                errors += [
                    ("Longitude must be a float", "error", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
            if not data.get(CACAO_1_1_GpsLocation.Field_Longitude.cacao_name):
                errors += [
                    ("Latitude is required if Longitude is provided", "error", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
        
    class Field_Precision(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Precision"
        cacao_name = "precision"
        label = "Precision"
        
        @classmethod
        def validate_field_json(cls, data, *args, **kwargs):
            valid, errors = super().validate_field_json(data)
            if not valid:
                return False, errors
            if not data.get(cls.cacao_name):
                return True, errors
            try:
                float(data[cls.cacao_name])
            except ValueError:
                errors += [
                    ("Precision must be a float or int", "error", 
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
            if not (data.get(CACAO_1_1_GpsLocation.Field_Longitude.cacao_name) and
                    data.get(CACAO_1_1_GpsLocation.Field_Latitude.cacao_name)):
                errors += [
                    ("Longitude and Latitude are required if Precision is provided", "error",
                     (json.dumps(data), cls.cacao_name, json.dumps(data[cls.cacao_name])))]
    
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    
class CACAO_1_1_Signature(CACAO_1_1_PlaybookObject):
    cls_form = "Signature"
    cls_label = "Signature"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        allowed_values = ["signature"]
    class Field_SpecVersion(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Spec version"
        cacao_name = "spec_version"
        label = "Spec Version"
        allowed_values = ["1.1"]
    class Field_Id(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Id"
        cacao_name = "id"
        label = "Id"
        identifier_prefix = "signature--"
    class Field_CreatedBy(CACAO_1_1_PlaybookObject.Abstract_Field_CreatedBy):
        pass
    class Field_Created(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = True
        field_name = "Created"
        cacao_name = "created"
        label = "Created"
    class Field_Modified(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = True
        field_name = "Modified"
        cacao_name = "modified"
        label = "Modified"
    class Field_Revoked(CACAO_1_1_PlaybookObject.Boolean_Field):
        field_type = FT.boolean
        required = False
        field_name = "Revoked"
        cacao_name = "revoked"
        label = "Revoked"
    class Field_Signee(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Signee"
        cacao_name = "signee"
        label = "Signee"
    class Field_ValidFrom(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = False
        field_name = "Valid from"
        cacao_name = "valid_from"
        label = "Valid From"
    class Field_ValidUntil(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = False
        field_name = "Valid until"
        cacao_name = "valid_until"
        label = "Valid Until"
    class Field_RelatedTo(CACAO_1_1_PlaybookObject.Identifier_Field):
        field_type = FT.identifier
        required = True
        field_name = "Related to"
        cacao_name = "related_to"
        label = "Related To"
        identifier_prefix = "playbook--"
    class Field_RelatedVersion(CACAO_1_1_PlaybookObject.Abstract_Field_Timestamp):
        field_type= FT.timestamp
        required = True
        field_name = "Related version"
        cacao_name = "related_version"
        label = "Related Version"
    class Field_Sha256(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Sha256"
        cacao_name = "sha256"
        label = "Sha256"
    class Field_Algorithm(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Algorithm"
        cacao_name = "algorithm"
        label = "Algorithm"
        allowed_values = [
            'RS256',
            'RS384',
            'RS512',
            'ES256',
            'ES384',
            'ES512',
            'PS256',
            'PS384',
            'PS512',
            'Ed25519',
            'Ed448',
        ]
    class Field_PublicKeys(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Public keys"
        cacao_name = "public_keys"
        label = "Public Keys"
    class Field_CertUrl(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Cert url"
        cacao_name = "cert_url"
        label = "Cert Url"
    
    class Field_Thumbprint(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Thumbprint"
        cacao_name = "thumbprint"
        label = "Thumbprint"
    
    class Field_Value(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = True
        field_name = "Value"
        cacao_name = "value"
        label = "Value"
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
class CACAO_1_1_Variable(CACAO_1_1_PlaybookObject):
    cls_form = "Variable"
    cls_label = "Variable"
    class Meta:
        proxy = True
    
    class Field_Type(CACAO_1_1_PlaybookObject.Abstract_Field_Type):
        allowed_values = [
            'string',
            'uuid',
            'integer',
            'long',
            'mac-address',
            'ipv4-addr',
            'ipv6-addr',
            'uri',
            'sha256-hash',
            'hexstring',
            'dictionary',
        ]
    
    class Field_Description(CACAO_1_1_PlaybookObject.Abstract_Field_Description):
        pass
    class Field_Value(CACAO_1_1_PlaybookObject.String_Field):
        field_type = FT.string
        required = False
        field_name = "Value"
        cacao_name = "value"
        label = "Value"
    class Field_Constant(CACAO_1_1_PlaybookObject.Boolean_Field):
        field_type = FT.boolean
        required = False
        field_name = "Constant"
        cacao_name = "constant"
        label = "Constant"
    class Field_External(CACAO_1_1_PlaybookObject.Boolean_Field):
        field_type = FT.boolean
        required = False
        field_name = "External"
        cacao_name = "external"
        label = "External"
    
    object_fields = CACAO_1_1_PlaybookObject.object_fields.copy()
    object_fields.update({
        cls.__name__: cls for cls in locals().values()
        if isinstance(cls, type) and 
        issubclass(cls, CACAO_1_1_PlaybookObject.Object_Field) and 
        cls.__name__.startswith("Field_")
    })
    
    def get_cacao_id(self):
        return f"$${self.wiki_page_name.split('--')[-1].replace(' ', '_')}$$"
    
    @classmethod
    def generate_wiki_name(cls, *args, name:str=None, **kwargs):
        if name:
            return f"Variable--{uuid.uuid4()}--{name[2:-2]}"
        return f"Variable--{uuid.uuid4()}--VarName{uuid.uuid4()}"