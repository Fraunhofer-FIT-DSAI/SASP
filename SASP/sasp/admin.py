from django.contrib import admin

from sasp.models import (
    Playbook,
    Playbook_Object,
    Semantic_Relation,
    Automation_Instance,
)
from sasp.models.auth import UserProfile, LoginInfo

# Register your models here.
# admin.site.register(Playbook)
# admin.site.register(Playbook_Object)


class Playbook_ObjectInline(admin.TabularInline):
    model = Playbook_Object
    extra = 0


@admin.register(Playbook)
class PlaybookAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "last_change", "wiki_page_name")
    list_filter = ("name", "description", "last_change", "wiki_page_name")
    search_fields = ("name", "description", "last_change", "wiki_page_name")
    ordering = ("name", "description", "last_change", "wiki_page_name")

    inlines = [Playbook_ObjectInline]


@admin.register(Playbook_Object)
class Playbook_ObjectAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "last_change", "wiki_page_name", "playbook")
    list_filter = ("name", "description", "last_change", "wiki_page_name", "playbook")
    search_fields = ("name", "description", "last_change", "wiki_page_name", "playbook")
    ordering = ("name", "description", "last_change", "wiki_page_name", "playbook")


@admin.register(Semantic_Relation)
class Semantic_RelationAdmin(admin.ModelAdmin):
    list_display = ("subject_field", "predicate", "object_field", "playbook")
    list_filter = ("subject_field", "predicate", "object_field", "playbook")
    search_fields = ("subject_field", "predicate", "object_field", "playbook")
    ordering = ("subject_field", "predicate", "object_field", "playbook")


@admin.register(Automation_Instance)
class Automation_InstanceAdmin(admin.ModelAdmin):
    list_display = ("playbook", "case_id", "case_name", "status", "last_update")
    list_filter = ("playbook", "case_id", "case_name", "status", "last_update")
    search_fields = ("playbook", "case_id", "case_name", "status", "last_update")
    ordering = ("playbook", "case_id", "case_name", "status", "last_update")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name")
    list_filter = ("user", "display_name")
    search_fields = ("user", "display_name")
    ordering = ("user", "display_name")


@admin.register(LoginInfo)
class LoginInfoAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "url",
        "username",
        "password",
        "cert",
        "token",
        "expires",
    )
    list_filter = (
        "user",
        "name",
        "url",
        "username",
        "password",
        "cert",
        "token",
        "expires",
    )
    search_fields = (
        "user",
        "name",
        "url",
        "username",
        "password",
        "cert",
        "token",
        "expires",
    )
    ordering = (
        "user",
        "name",
        "url",
        "username",
        "password",
        "cert",
        "token",
        "expires",
    )
