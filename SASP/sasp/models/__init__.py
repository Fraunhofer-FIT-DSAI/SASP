from typing import Any
from django.db import models, transaction, connection, IntegrityError
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from sasp.pytools import classproperty, iter_subclasses

from copy import copy

import logging
import uuid
import enum
import time


class Playbook(models.Model):
    class Automation:
        """If the playbook is automated, the automation class should be implemented."""
        class AutomationException(Exception):
            field_name = None
            traceback = None
            def __init__(self, message, *args, **kwargs):
                self.field_name = kwargs.pop("field_name", None)
                self.traceback = kwargs.pop("traceback", None)
                self.message = message
                super().__init__(message, *args, **kwargs)
        
        class AutomationNotReadyException(AutomationException):
            pass
        
        class AutomationExecutionException(AutomationException):
            pass
        
        class AutomationTimeoutException(AutomationException):
            pass
        
        def __init__(self, playbook: 'Playbook', *args, **kwargs):
            """Initializes the automation with the playbook object."""
            self.playbook = playbook
            self.ready_errors = []
            self.execution_errors = []
            
            self.db_object = None
                
        def ready_error(self, exception: AutomationNotReadyException):
            self.ready_errors.append(exception)
        
        def ready(self) -> bool:
            """Returns whether the automation is ready to be executed."""
            raise NotImplementedError("This method should be implemented by the subclass")
        
        def get_context(self) -> dict:
            """Returns the context dictionary for the automation."""
            raise NotImplementedError("This method should be implemented by the subclass")
        
        @classmethod
        def get_context_form(cls):
            raise NotImplementedError("This method should be implemented by the subclass")
        
        @classmethod
        def execute(cls, *args, **kwargs) -> 'Automation_Instance':
            """Executes the Playbook."""
            raise NotImplementedError("This method should be implemented by the subclass")
        
        @classmethod
        def supported(cls) -> bool:
            """Returns whether the automation is supported by the current environment."""
            return False
    class Deserializer:
        """Every playbook object should have a deserializer that can be used to import the object from JSON data
        and implements these following methods:
        """
        class DeserializationException(Exception):
            field_name = None
            traceback = None
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.field_name = kwargs.get("field_name", None)
                self.traceback = kwargs.get("traceback", None)
        
        def __init__(
            self, 
            json_data: dict,
            *args,
            **kwargs
            ):
            """Initializes the deserializer with the JSON data."""
            self.json_data = json_data
        
        def validate(self):
            """Validate that the JSON data is correct and can be deserialized.
            Raises DeserializationException if the data is incorrect.
            """
            raise NotImplementedError("This method should be implemented by the subclass")
        def deserialize(self, *args, **kwargs):
            """Deserializes the JSON data to a playbook object."""
            raise NotImplementedError("This method should be implemented by the subclass")
        
        def save(self):
            """Saves the deserialized playbook object to the database."""
            raise NotImplementedError("This method should be implemented by the subclass")
        
        @classmethod
        def supported(cls) -> bool:
            """Returns whether the deserializer is supported by the current environment."""
            return False
    class Meta:
        ordering = ["name"]
        # Constraints
        # wiki_page_name must be unique unless the object is archived
        # If archived, archived_on and archive_tag must be set
        constraints = [
            models.UniqueConstraint(
                fields=["wiki_page_name"],
                condition=models.Q(archive_tag__isnull=True),
                name="playbook_unique_wiki_page_name_when_archive_tag_is_null",
                violation_error_message="The wiki page name must be unique unless the playbook is archived",
            ),
            models.UniqueConstraint(
                fields=["wiki_page_name", "archive_tag"], 
                name="playbook_unique_wiki_page_name",
                violation_error_message="Archive tags must be unique for each playbook",
            ),
            models.CheckConstraint(
                condition=(models.Q(archived_on__isnull=False) & models.Q(archive_tag__isnull=False))
                | (models.Q(archived_on__isnull=True) & models.Q(archive_tag__isnull=True)),
                name="playbook_archive_tag_and_archived_on",
                violation_error_message="If the playbook is archived, both the archive tag and the archived on date must be set",
            ),
        ]
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    last_change = models.DateTimeField(auto_now=True, auto_now_add=False)
    wiki_page_name = models.CharField(max_length=200, editable=False)
    wiki_form = models.CharField(max_length=200, editable=False)
    archived_on = models.DateTimeField(null=True, blank=True, editable=False)
    archive_tag = models.CharField(max_length=200, null=True, blank=True)
    permission_view = models.JSONField(default=dict)
    permission_edit = models.JSONField(default=dict)
    root_object = None
    
    logger = logging.getLogger(__name__)
    
    @property
    def archived(self):
        return self.archived_on is not None

    @classproperty
    def slug(cls) -> str:
        """Returns the slug of the object."""
        raise NotImplementedError("This method should be implemented by the subclass")

    _proxyclasses = None
    @classproperty
    def proxyclasses(cls) -> list:
        """Returns a list of all instantiable proxy classes of the object."""
        if cls._proxyclasses:
            return cls._proxyclasses
        cls._proxyclasses = [
            subclass
            for subclass in iter_subclasses(cls)
            if subclass != cls and hasattr(subclass, "cls_form")
        ]
        return cls._proxyclasses

    _playbook_object_class = None
    @classproperty
    def playbook_object_class(cls):
        raise NotImplementedError("This method should be implemented by the subclass")
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def get_properties(cls) -> list:
        """Returns all properties used by the class."""
        raise NotImplementedError("This method should be implemented by the subclass")

    @classmethod
    def get_templates(cls) -> dict:
        """Returns all templates used by the class."""
        raise NotImplementedError("This method should be implemented by the subclass")

    def get_url(self) -> str:
        """Returns the URL of the object."""
        return reverse("playbook-detail", kwargs={"pk": self.pk})

    def _init_permissions(self):
        if self.permission_view == dict():
            self.permission_view = {"public": True, "groups": [], "users": []}
        if self.permission_edit == dict():
            self.permission_edit = {"public": True, "groups": [], "users": []}

    def has_permission(self, user, permission_type):
        """
        This method checks if the user has the specified permission for the playbook.

        User at this point is just a string that uniquely identifies the user.
        # TAG:PERMISSIONS TAG:KEYCLOAK TAG:MULTIPLE_USERS
        """
        if permission_type not in ["view", "edit"]:
            raise Exception(f"Invalid permission type: {permission_type}")
        self._init_permissions()
        if permission_type == "view":
            permission = self.permission_view
        elif permission_type == "edit":
            permission = self.permission_edit
        if permission["public"]:
            return True
        if user in permission["users"]:
            return True
        if user in permission["groups"]:
            # TODO: Implement group based permissions
            raise Exception(
                "Group based permissions are not yet implemented, but the user is in a group that has permission"
            )
        return False

    def set_permission(self, identifier, permission_type, is_group=False):
        """
        This method sets the permission for the playbook to True.

        Args:
            identifier (str): The identifier of the user or group.
            permission_type (str): The type of permission to set, either "view" or "edit".
            is_group (bool): Whether the identifier is a group or a user.

        Returns:
            bool: True if the permission was set, False if it was already set.
        """

        self._init_permissions()
        if permission_type not in ["view", "edit"]:
            raise Exception(f"Invalid permission type: {permission_type}")
        if permission_type == "view":
            permission = self.permission_view
        elif permission_type == "edit":
            permission = self.permission_edit
        if is_group:
            if identifier in permission["groups"]:
                return False
            permission["groups"].append(identifier)
        else:
            if identifier in permission["users"]:
                return False
            permission["users"].append(identifier)
        self.save()
        return True

    def remove_permission(self, identifier, permission_type, is_group=False):
        """
        This method removes the permission for the playbook.

        Returns a boolean indicating whether the permission was already removed or not.

        Args:
            identifier (str): The identifier of the user or group.
            permission_type (str): The type of permission to remove, either "view" or "edit".
            is_group (bool): Whether the identifier is a group or a user.

        Returns:
            bool: True if the permission was removed, False if it wasn't present.
        """

        self._init_permissions()
        if permission_type not in ["view", "edit"]:
            raise Exception(f"Invalid permission type: {permission_type}")
        if permission_type == "view":
            permission = self.permission_view
        elif permission_type == "edit":
            permission = self.permission_edit
        if is_group:
            if identifier not in permission["groups"]:
                return False
            permission["groups"].remove(identifier)
        else:
            if identifier not in permission["users"]:
                return False
            permission["users"].remove(identifier)
        self.save()
        return True

    def resolve_subclass(self):
        if self.wiki_form is None:
            raise Exception("The wiki form of the playbook object is not set")

        proxy_class = Playbook.get_proxyclass(self.wiki_form)
        if (
            proxy_class == self.__class__
        ):  # Avoid infinite recursion and unnecessary object creation
            return self
        if proxy_class:
            # Create a new instance of the proxy class
            proxy_instance = proxy_class()

            # Copy attributes from the original instance to the proxy instance
            for field in self._meta.fields:
                setattr(proxy_instance, field.name, getattr(self, field.name))

            # Copy any additional attributes that might not be in _meta.fields
            for attr in self.__dict__:
                if attr not in proxy_instance.__dict__:
                    setattr(proxy_instance, attr, getattr(self, attr))

            # If the object has a pk (it was saved to the database), we need to explicitly set the pk of the proxy instance
            if self.pk:
                proxy_instance.pk = self.pk

            return proxy_instance

        return self

    @classmethod
    def get_proxyclass(cls, form_name: str, slug: bool = False):
        if slug:
            for subclass in cls.proxyclasses:
                try:
                    if subclass.slug == form_name:
                        return subclass
                except (
                    NotImplementedError
                ) as _:  # The subclass does not implement the slug method
                    continue
        else:
            for subclass in cls.proxyclasses:
                if getattr(subclass, "cls_form", None) == form_name:
                    return subclass
        raise KeyError(
            f"No subclass of Playbook matches the provided form name: {form_name}"
        )

    @classmethod
    def get_new_forms(cls) -> list:
        return cls.proxyclasses

    def get_absolute_url(self):
        return reverse("playbook-detail", kwargs={"pk": self.pk})

    def get_edit_url(self):
        return reverse("playbook-edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("playbook-delete", kwargs={"pk": self.pk})

    def update_context_view(self, context):
        """Updates the context dictionary with view specific information."""
        return context

    @classmethod
    def query(cls, *args, archived: str = "False", **kwargs) -> models.QuerySet:
        """Wrapper around the filter method that allows for filtering by archived status.

        Args:
            archived ['True', 'False', 'All']: The archived status to filter by.

        Raises:
            ValueError: If the value of archived is not one of the supported values.

        Returns:
            QuerySet: The filtered queryset.
        """
        if archived == "True":
            kwargs["archived_on__isnull"] = False
        elif archived == "All":
            pass
        elif archived == "False":
            kwargs["archived_on__isnull"] = True
        else:
            raise ValueError(f"Invalid value for archived: {archived}")
            
        return cls.objects.filter(*args, **kwargs)

    def get_label(self):
        value = None
        if self.name:
            value = self.name
        elif self.wiki_page_name:
            value = self.wiki_page_name
        elif self.pk:
            value = _("Unnamed playbook %(pk)s" % {"pk":self.pk})
        else:
            value = _("Unnamed playbook")
        
        if self.archived:
            value += _(" (Archived: %(archive_tag)s)" % {"archive_tag":self.archive_tag})
        return value

    def get_root(self):
        if self.root_object is None:
            self.root_object = self.playbook_objects.filter(
                wiki_page_name=self.wiki_page_name, playbook=self
            ).first()
            self.root_object = self.root_object.resolve_subclass()
        return self.root_object

    def get_tags(self):
        """
        This method returns the tags of the playbook, as a list of strings.
        """
        raise NotImplementedError("This method should be implemented by the subclass")

    def update_relations(self):
        pass

    def save(self, *args, **kwargs):
        if self.archived and self.pk is not None:
            raise models.ProtectedError("Archived playbooks cannot be modified")
        self.name = self.name or self.wiki_page_name
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def remove(self, *args, **kwargs):
        for obj in self.playbook_objects.all():
            obj.remove()
        super().delete(*args, **kwargs)

    def get_descriptive_dict(self):
        """Returns a dictionary with the most important information about the playbook.
        For displaying the playbook in a list, for example.
        The dictionary is comprised of human readable labels as keys and raw data as values.

        Returns:
            dict: The descriptive dictionary.
        """
        raise NotImplementedError("This method should be implemented by the subclass")
        return_dict = {
            "name": (self.name, "Name"),
            "description": (self.description, "Description"),
            "last_change": (self.last_change, "Last Change"),
            "wiki_page_name": (self.wiki_page_name, "Wiki Page Name"),
            "wiki_form": (self.wiki_form, "Wiki Form"),
            "pk": (self.pk, "PK"),
            "labels": (None, "Labels"),
            "author": (None, "Author"),
            "confidentiality": (None, "Confidentiality"),
            "standard": (None, "Standard"),
        }
        content = self.playbook_object.content
        if self.wiki_form == "Playbook":  # SAPPAN
            return_dict["labels"] = (content.get("HasPlaybookCategory", []), "Labels")
            return_dict["author"] = (content.get("HasAuthor", ""), "Author")
            return_dict["confidentiality"] = (
                content.get("HasConfidentiality", "d - TLP:WHITE"),
                "Confidentiality",
            )
            return_dict["standard"] = ("SAPPAN", "Standard")
        elif self.wiki_form == "CACAO Playbook":  # CACAO
            return_dict["labels"] = (content.get("Labels", []), "Labels")
            return_dict["author"] = (content.get("Created by", ""), "Author")
            return_dict["standard"] = (
                "CACAO " + content.get("Spec version", ["?"])[0],
                "Standard",
            )
            data_marking = self.playbook_objects.filter(wiki_form="TLP Marking")
            if data_marking:
                data_marking = data_marking[0]
                return_dict["confidentiality"] = (
                    data_marking.content.get("Tlp level", "TLP:WHITE"),
                    "Confidentiality",
                )
            else:
                return_dict["confidentiality"] = ("TLP:WHITE", "Confidentiality")
        else:
            raise Exception(f"Unsupported form type: {self.wiki_form}")
        return return_dict

    def matches(
        self,
        form_type: str = None,
        name: str = None,
        tags: list = None,
        author: str = None,
        confidentiality: str = None,
    ):
        """
        This method checks if the object matches the provided filters.
        """

        # Supported filters for now:
        # - Form Type
        # - Name
        # - tags/labels
        # - Author
        # - Confidentiality

        content = self.content
        if self.wiki_form == "Playbook":  # SAPPAN
            if form_type and form_type != "SAPPAN":
                return False
            if name:
                if name.lower().strip() not in self.name.lower():
                    return False
            if tags:
                if not all(
                    tag in content.get("HasPlaybookCategory", []) for tag in tags
                ):
                    return False
            if author:
                if author.lower().strip() not in content.get("HasAuthor", "").lower():
                    return False
            if confidentiality:
                conf, conf_key = {
                    "tlp:white": (0, "d - TLP:WHITE"),
                    "tlp:green": (1, "d - TLP:GREEN"),
                    "tlp:amber": (2, "d - TLP:AMBER"),
                    "tlp:red": (3, "d - TLP:RED"),
                }.get(confidentiality.lower(), (None, None))
                if conf is None:
                    raise Exception(
                        f"Unsupported confidentiality level: {confidentiality}"
                    )
                obj_conf, obj_conf_key = {
                    "d - TLP:WHITE": 0,
                    "d - TLP:GREEN": 1,
                    "d - TLP:AMBER": 2,
                    "d - TLP:RED": 3,
                }.get(content.get("HasConfidentiality", "d - TLP:WHITE"))
                if obj_conf > conf:
                    return False
            return True
        elif self.wiki_form == "CACAO Playbook":  # CACAO
            if form_type and form_type != "CACAO":
                return False
            if name:
                if name.lower().strip() not in self.name.lower():
                    return False
            if tags:
                if not all(tag in content.get("Labels", []) for tag in tags):
                    return False
            if author:
                if author.lower().strip() not in content.get("Created by", "").lower():
                    return False
            if confidentiality:
                data_marking = self.playbook_objects.filter(wiki_form="TLP Marking")
                conf_dict = {
                    "tlp:white": 0,
                    "tlp:green": 1,
                    "tlp:amber": 2,
                    "tlp:red": 3,
                }
                conf = conf_dict[confidentiality.lower()]

                if data_marking:
                    data_marking = data_marking[0]
                    conf_obj = data_marking.content.get("Tlp level")
                    conf_obj = conf_dict[conf_obj.lower()]
                else:
                    conf_obj = 0
                if conf_obj > conf:
                    return False
        else:
            raise Exception(f"Unsupported form type: {self.wiki_form}")

    # Stub methods that should be implemented by the subclasses
    def get_new_objects(self) -> list:
        """Returns a list of new objects that can be directly created from the playbook."""
        return []

    def get_confidentiality(self):
        """Returns the confidentiality level of the playbook.

        Must return a string from the following list:
        - "TLP:WHITE"
        - "TLP:GREEN"
        - "TLP:AMBER"
        - "TLP:RED"
        """
        raise NotImplementedError("This method should be implemented by the subclass")

    def get_cls_label(self):
        """Returns a human readable label for the form of the playbook."""
        return self.wiki_form

    def get_name(self):
        """Returns the name of the playbook."""
        return self.name

    @classmethod
    def is_json_representation(cls, json_data):
        """Checks if the provided JSON data represents a playbook of this type."""
        raise NotImplementedError("This method should be implemented by the subclass")

    @classmethod
    def new_from_json(cls, json_data):
        """Creates a new playbook from the provided JSON data."""
        for sub_cls in cls.__subclasses__():
            try:
                if sub_cls.is_json_representation(json_data):
                    return sub_cls.new_from_json(json_data)
            except NotImplementedError as _:
                cls.logger.error(
                    f"Class {sub_cls} does not implement the is_json_representation method"
                )
                continue
        raise Exception("No subclass of Playbook matches the provided JSON data")

    def register_object(self, object):
        """Registers an object with the playbook."""
        pass
    
    @classmethod
    def make_archive(cls, playbook:'Playbook', archive_tag:str):
        """
        This method creates an archived version of the playbook.
        """
        if playbook.archived:
            raise Exception("The playbook is already archived")
        
        playbook = copy(playbook)
        
        playbook_objects = [x for x in playbook.playbook_objects.all()]
        
        playbook.pk = None
        playbook._state.adding = True
        playbook.archived_on = timezone.now()
        playbook.archive_tag = archive_tag
        
        for obj in playbook_objects:
            obj.pk = None
            obj._state.adding = True
            obj.playbook = playbook
            obj.archived = True
        
        try:
            with transaction.atomic():
                playbook.save()
                for obj in playbook_objects:
                    obj.save()
        except IntegrityError as e:
            cls.logger.error(f"Error while archiving playbook: {e}")
            raise Exception("Error while archiving playbook")
        
        playbook.resolve_subclass().update_relations()
        
        return playbook
    
    
    def __str__(self):
        return self.get_label()

class Playbook_Object(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    last_change = models.DateTimeField(auto_now=True)
    wiki_page_name = models.CharField(max_length=200)
    playbook = models.ForeignKey(
        to="Playbook",
        on_delete=models.CASCADE,
        related_name="playbook_objects",
        null=True,
        blank=True,
    )
    content = models.JSONField(default=dict)
    wiki_form = models.CharField(max_length=200, null=True, blank=True)
    archived = models.BooleanField(default=False)
    cls_form = None
    cls_label = "Playbook Object"
    logger = logging.getLogger(__name__)

    @classproperty
    def slug(cls) -> str:
        """Returns the slug of the object."""
        return None

    _proxyclasses = None

    @classproperty
    def proxyclasses(cls) -> list:
        """Returns a list of all instantiable proxy classes of the object."""
        if cls._proxyclasses:
            return cls._proxyclasses
        cls._proxyclasses = [
            subclass
            for subclass in iter_subclasses(cls)
            if subclass != cls and subclass.cls_form
        ]
        return cls._proxyclasses

    _playbook_class = None

    @classproperty
    def playbook_class(cls):
        raise NotImplementedError("This method should be implemented by the subclass")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["wiki_page_name"],
                condition=models.Q(archived=False),
                name="pb_object_unique_wiki_page_name",
                violation_error_message="The wiki page name must be unique",
            ),
        ]

    class Object_Field:
        def serialize_field(self, *args, **kwargs):
            """Serializes the field to a dictionary."""
            raise NotImplementedError(
                "This method should be implemented by the subclass"
            )

        def deserialize_field(self, data, *args, **kwargs):
            """Deserializes the field from a dictionary."""
            raise NotImplementedError(
                "This method should be implemented by the subclass"
            )

        # NOTE: We assume data in our db to be correct, and accept faulty exports
        # With this structure where every object gets a subclass, we should write validators for input
        # during object creation via the GUI as well, but one thing at a time
        @classmethod
        def validate_field(cls, data, *args, **kwargs):
            """Validates that the contents of the field are valid for deserialization.
            Returns:
                bool: True if the contents are valid or valid with warnings, False if the contents are invalid.
                list: A list of three-tuples with the first element being the error message, the second element being
                the severity of the error ('critical', 'error', 'warning', 'info') and the third element being the context of the error.
            """
            raise NotImplementedError(
                "This method should be implemented by the subclass"
            )

    def serialize_object(self, *args, **kwargs):
        """Serializes the playbook object to a dictionary."""
        raise NotImplementedError("This method should be implemented by the subclass")

    def deserialize_object(self, *args, **kwargs):
        """Deserializes the dictionary to a playbook object."""
        raise NotImplementedError("This method should be implemented by the subclass")

    @classmethod
    def validate_json(cls, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by the subclass")

    def resolve_subclass(self):
        if self.wiki_form is None:
            raise Exception("The wiki form of the playbook object is not set")

        proxy_class = self.get_proxyclass(self.wiki_form)
        if (
            proxy_class == self.__class__
        ):  # Avoid infinite recursion and unnecessary object creation
            return self
        if proxy_class:
            # Create a new instance of the proxy class
            proxy_instance = proxy_class()

            # Copy attributes from the original instance to the proxy instance
            for field in self._meta.fields:
                setattr(proxy_instance, field.name, getattr(self, field.name))

            # Copy any additional attributes that might not be in _meta.fields
            for attr in self.__dict__:
                if attr not in proxy_instance.__dict__:
                    setattr(proxy_instance, attr, getattr(self, attr))

            # If the object has a pk (it was saved to the database), we need to explicitly set the pk of the proxy instance
            if self.pk:
                proxy_instance.pk = self.pk

            return proxy_instance

        return self

    @classmethod
    def get_proxyclass(cls, form_name: str, slug: bool = False):
        if slug:
            if cls.slug == form_name:
                return cls
            for subclass in cls.proxyclasses:
                try:
                    if subclass.slug == form_name:
                        return subclass
                except (
                    NotImplementedError
                ) as _:  # The subclass does not implement the slug method
                    continue
        else:
            if getattr(cls, "cls_form", None) == form_name:
                return cls
            for subclass in cls.proxyclasses:
                if getattr(subclass, "cls_form", None) == form_name:
                    return subclass
        raise KeyError(
            f"No subclass of Playbook Object matches the provided form name: '{form_name}'"
        )

    # @classmethod
    # def from_db(cls, db, field_names, values):
    #     instance = super().from_db(db, field_names, values)
    #     return instance.resolve_subclass()

    def get_absolute_url(self):
        return reverse(
            "playbook_object-detail", kwargs={"pk": self.pk, "pk_pb": self.playbook.pk}
        )

    def get_edit_url(self):
        return reverse(
            "playbook_object-edit", kwargs={"pk": self.pk, "pk_pb": self.playbook.pk}
        )

    def get_delete_url(self):
        return reverse(
            "playbook_object-delete", kwargs={"pk": self.pk, "pk_pb": self.playbook.pk}
        )

    def update_context_view(self, context):
        """Updates the context dictionary with view specific information."""
        return context

    @classmethod
    def generate_wiki_name(cls, *args, **kwargs):
        raise NotImplementedError(
            f"generate_wiki_name not implemented for class {cls.__name__}"
        )

    def get_form_fields(self):
        raise NotImplementedError("This method should be implemented by the subclass")

    def get_form_class(self):
        raise NotImplementedError("This method should be implemented by the subclass")

    def read_from_wiki(self):
        """
        This method loads the content of the playbook object from the wiki.
        """
        raise NotImplementedError(
            "Instructions on how to read from wiki should be set in the subclass"
        )

    def write_to_wiki(self):
        """
        This method saves the content of the playbook object to the wiki.
        """
        raise NotImplementedError(
            "Instructions on how to write to wiki should be set in the subclass"
        )

    def make_relations(self):
        """
        This method creates semantic relations between the playbook object and other objects.
        """
        raise NotImplementedError(
            "Instructions on how to make relations should be set in the subclass"
        )

    # Do not use this unless you only want to write the object,
    # for updating the wiki page and semantic relations, use the full_save method
    def save(self, *args, **kwargs):
        if self.archived and self.pk is not None:
            raise models.ProtectedError("Archived playbook objects cannot be modified")
        super().save(*args, **kwargs)

    def full_save(self, *args, **kwargs):
        skip_wiki = kwargs.pop("skip_wiki", False)
        skip_relations = kwargs.pop("skip_relations", False)
        if not skip_wiki and not self.archived:
            self.write_to_wiki()
        if not skip_relations:
            self.make_relations()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def remove(self, *args, **kwargs):
        pass

    def __str__(self):
        return self.name

    # Stub methods that should be implemented by the subclasses
    def get_new_objects(self) -> list:
        """Returns a list of new objects that can be directly created from the playbook object."""
        return []

    @classmethod
    def get_new_forms(cls) -> list:
        return cls.proxyclasses

    def get_cls_label(self):
        """Returns a human readable label for the form of the playbook object."""
        return self.wiki_form
    
    def get_name(self):
        """Returns the name of the playbook object."""
        return self.name or self.wiki_page_name
    
    def get_label(self):
        value = self.get_name() or self.cls_label
        if self.archived:
            value += _(" (Archived)")
        return value

    def add_to_field(self, field_name: str, value: str):
        """Adds a value to a field in the playbook object."""
        self.content[field_name] = self.content.get(field_name, []) + [value]

    def initial_fill(self):
        """Returns a dictionary with suggested initial values for a new playbook object."""
        return {}

    def get_context(self, **kwargs):
        """Returns a dictionary with of playbook object specific context for template rendering."""
        return {}

    def bpmn(self):
        """Generates a BPMN representation of the playbook object, updates the wiki page and returns the BPMN XML."""
        raise NotImplementedError("This method should be implemented by the subclass.")

    def get_next_objects(self):
        """Returns a dictionary of objects this playbook object is pointing to."""
        return {}

    def get_fields(self):
        """Returns a list of fields for the playbook object."""
        return []

class Semantic_Relation(models.Model):
    """
    This class represents a semantic relation between two Playbook_Objects, (note playbooks themselves also have a playbook_object representation)
    """

    # Using wiki_page_name as a foreign key is not ideal, but it is the only way to ensure consistency between the wiki and the database
    subject_field = models.ForeignKey(
        to="Playbook_Object",
        on_delete=models.CASCADE,
        related_name="semantic_relations",
        null=True,
        blank=True,
    )
    object_field = models.ForeignKey(
        to="Playbook_Object",
        on_delete=models.CASCADE,
        related_name="semantic_sources",
        null=True,
        blank=True,
    )
    predicate = models.CharField(
        max_length=200
    )  # The predicate of the relation (e.g. "next_steps" or "has_role")

    # Improve searchability by adding a reference to the playbook, should narrow down the search space
    playbook = models.ForeignKey(
        to="Playbook",
        on_delete=models.CASCADE,
        related_name="semantic_relations",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.subject_field + " " + self.predicate + " " + self.object_field

    class Meta:
        ordering = ["subject_field", "predicate", "object_field"]
        indexes = [
            models.Index(fields=["playbook"]),
        ]

class Automation_Instance(models.Model):
    """
    This class represents an instance of the automated execution of a playbook, via the Hive. It is used to track the status of the execution
    and communicate with the thread that is executing the playbook.
    """
    class Status(str, enum.Enum):
        def __new__(cls, value: str, label):
            obj = str.__new__(cls, value)
            obj._value_ = value
            obj.label = label
            return obj
        
        INITIALIZED = ("Initialized", _("Initialized"))
        RUNNING = ("Running", _("Running"))
        COMPLETED = ("Completed", _("Completed"))
        ERROR = ("Error", _("Error"))
        CANCELED = ("Canceled", _("Canceled"))
        

    # The playbook that is being executed
    playbook = models.ForeignKey(
        to="Playbook",
        on_delete=models.CASCADE,
        related_name="automation_instances",
        null=True,
        blank=True,
    )
    # A json representation of the playbook at the time of execution
    playbook_frozen = models.JSONField(default=dict, null=False, blank=True)
    # A wiki_name:Status dictionary of the playbook objects that are being executed
    objects_state = models.JSONField(default=dict, null=False, blank=True)
    
    # The case that is being executed
    case_id = models.CharField(max_length=200, null=True, blank=True)
    case_name = models.CharField(max_length=200, null=True, blank=True)
    # The status of the execution
    status = models.CharField(max_length=200, null=True, blank=True)
    # The output of the execution
    output = models.JSONField(null=True, blank=True)
    output_updates = []
    # Object for registering confirmation requests
    confirmation_requests = models.JSONField(default=dict, null=False, blank=True)
    last_update = models.DateTimeField(auto_now=True)
    # The time the execution was started
    started = models.DateTimeField(auto_now_add=True)
    # The time the execution was completed
    completed = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
    
    @property
    def status_label(self):
        return self.Status(self.status).label

    def initialize(self, playbook, playbook_frozen, case_id, case_name):
        """
        This method gets a new instance ready for execution.
        """
        self.status = self.Status.INITIALIZED.value
        self.playbook = playbook
        self.playbook_frozen = playbook_frozen
        self.case_id = case_id
        self.case_name = case_name
        self.save()
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
    @transaction.atomic
    def complete(self, status: Status):
        """
        This method marks the execution as completed.
        """
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        obj.status = status.value
        obj.completed = timezone.now()
        obj.save()
        return obj

    def get_run_info(self):
        """
        This method returns a dictionary containing information about the current run.
        """
        run_info = {
            "playbook": self.playbook.get_label(),
            "case_id": self.case_id or "None",
            "status": self.status_label,
            "started": self.started,
            "completed": self.completed,
            "last_update": self.last_update,
            # "json_representation": self.output,
        }
        run_info["output"] = self.output or []
        return run_info
        
    def update_output(self, value, objects_state=None):
        obj = self.update_output_transaction(value, objects_state)
        self.output_updates.append(time.time())
        self.output_updates = [x for x in self.output_updates if time.time() - x < 1]
        if len(self.output_updates) > 5:
            # If the output is updated too frequently, web requests will be blocked
            # so we throttle the updates a bit
            time.sleep(1)
        return obj
        
    @transaction.atomic
    def update_output_transaction(self, value, objects_state=None):
        """
        This method updates the output of the execution, by updating the value at the specified path. In a thread safe manner.
        """
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        if obj.output:
            obj.output = [value] + obj.output
        else:
            obj.output = [value]
        
        if objects_state:
            obj.objects_state = objects_state
        
        obj.save()
        return obj

    @transaction.atomic
    def register_confirmation_request(self, command_info):
        # Read the object from the database
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        cmd_uuid = str(uuid.uuid4())

        if cmd_uuid in obj.confirmation_requests:
            self.logger.error(
                f"Confirmation request {command_info.get('title',None)} already exists"
            )
            raise Exception(
                f"Confirmation request {command_info.get('title',None)} already exists"
            )
        obj.confirmation_requests[cmd_uuid] = command_info
        obj.save()
        return cmd_uuid

    @transaction.atomic
    def remove_confirmation_request(self, cmd_uuid):
        # Read the object from the database
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        if cmd_uuid not in obj.confirmation_requests:
            self.logger.error(f"Confirmation request {cmd_uuid} does not exist")
            raise Exception(f"Confirmation request {cmd_uuid} does not exist")
        del obj.confirmation_requests[cmd_uuid]
        obj.save()

    @transaction.atomic
    def approve_confirmation_request(self, cmd_uuid):
        # Read the object from the database
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        if cmd_uuid not in obj.confirmation_requests:
            self.logger.error(f"Confirmation request {cmd_uuid} does not exist")
            raise Exception(f"Confirmation request {cmd_uuid} does not exist")
        obj.confirmation_requests[cmd_uuid]["approved"] = True
        obj.save()

    @transaction.atomic
    def abort_confirmation_request(self, cmd_uuid):
        # Read the object from the database
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        if cmd_uuid not in obj.confirmation_requests:
            self.logger.error(f"Confirmation request {cmd_uuid} does not exist")
            raise Exception(f"Confirmation request {cmd_uuid} does not exist")
        obj.confirmation_requests[cmd_uuid]["abort"] = True
        obj.save()

    @transaction.atomic
    def get_confirmation_request(self, cmd_uuid):
        # Read the object from the database
        # NOTE: sqlite does not support select_for_update, so this method will not work with sqlite
        if connection.vendor == "sqlite":
            obj = self
        elif connection.vendor in ["postgresql", "mysql", "oracle"]:
            obj = self.get_queryset().select_for_update().get()
        else:
            raise Exception("Unsupported database")

        obj.refresh_from_db()

        if cmd_uuid not in obj.confirmation_requests:
            self.logger.error(f"Confirmation request {cmd_uuid} does not exist")
            raise Exception(f"Confirmation request {cmd_uuid} does not exist")
        return obj.confirmation_requests[cmd_uuid]

    def __str__(self):
        return f"{self.playbook} - {self.case_id if self.case_id else _('No case id')} - {self.status}"


# Import at bottom because of circular dependencies
import sasp.models.cacao_1_1
import sasp.models.sappan
