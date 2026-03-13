from django.contrib import admin

from .models import Module, PermissionType, Role, RolePermission, UserRole


class PermissionTypeInline(admin.TabularInline):
    model = PermissionType
    extra = 1
    fields = ["name", "codename", "description", "order"]
    prepopulated_fields = {"codename": ("name",)}


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon", "is_active", "order", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [PermissionTypeInline]
    ordering = ["order", "name"]


@admin.register(PermissionType)
class PermissionTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "codename", "module", "order"]
    list_filter = ["module"]
    search_fields = ["name", "codename", "module__name"]
    ordering = ["module__order", "module__name", "order"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "is_default", "priority", "created_at"]
    list_filter = ["is_active", "is_default"]
    search_fields = ["name", "description"]
    filter_horizontal = ["permissions"]
    ordering = ["-priority", "name"]


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ["module", "permission_type"]
    list_filter = ["module"]
    search_fields = ["module__name", "permission_type__name"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "role",
        "assigned_by",
        "assigned_at",
        "expires_at",
        "is_active",
    ]
    list_filter = ["is_active", "role", "assigned_at"]
    search_fields = ["user__username", "user__email", "role__name"]
    raw_id_fields = ["user", "role", "assigned_by"]
    ordering = ["-assigned_at"]
    date_hierarchy = "assigned_at"
