from __future__ import annotations

from django.db import transaction

from .models import Module, PermissionType, Role, RolePermission, UserRole


CORE_PERMISSION_TYPES = (
    ("view", "View"),
    ("add", "Add"),
    ("edit", "Edit"),
    ("delete", "Delete"),
)

CORE_PERMISSION_CODES = {code for code, _ in CORE_PERMISSION_TYPES}


def get_role_permission_matrix(role=None):
    """Return active modules and permissions grouped for the role form UI."""
    modules = (
        Module.objects.filter(is_active=True)
        .prefetch_related("permission_types")
        .order_by("order", "name")
    )

    selected_permission_ids = set()
    if role is not None:
        selected_permission_ids = set(
            role.permissions.values_list("id", flat=True)
        )

    matrix = []
    for module in modules:
        module_permissions = []
        for permission_type in module.permission_types.all().order_by(
            "order", "name"
        ):
            role_permission, _ = RolePermission.objects.get_or_create(
                module=module,
                permission_type=permission_type,
            )
            module_permissions.append(
                {
                    "id": role_permission.id,
                    "name": permission_type.name,
                    "codename": permission_type.codename,
                    "description": permission_type.description,
                    "is_core": permission_type.codename in CORE_PERMISSION_CODES,
                    "selected": role_permission.id in selected_permission_ids,
                }
            )

        core_permissions = [
            permission
            for permission in module_permissions
            if permission["is_core"]
        ]
        extra_permissions = [
            permission
            for permission in module_permissions
            if not permission["is_core"]
        ]

        matrix.append(
            {
                "module": module,
                "permissions": module_permissions,
                "core_permissions": core_permissions,
                "extra_permissions": extra_permissions,
                "selected_count": sum(
                    1 for permission in module_permissions if permission["selected"]
                ),
                "selected_core_count": sum(
                    1 for permission in core_permissions if permission["selected"]
                ),
                "is_selected": any(
                    permission["selected"] for permission in module_permissions
                ),
            }
        )

    return matrix


@transaction.atomic
def save_role_permissions(role, permission_ids):
    """Replace a role's permissions from the selected RolePermission ids."""
    valid_ids = {
        int(permission_id)
        for permission_id in permission_ids
        if str(permission_id).strip().isdigit()
    }
    permissions = RolePermission.objects.filter(id__in=valid_ids)
    role.permissions.set(permissions)


def assign_default_role_to_user(user, assigned_by=None):
    """Assign the configured default dynamic role for the user's built-in type."""
    if not getattr(user, "role", ""):
        return None

    role = (
        Role.objects.filter(
            is_active=True,
            is_default=True,
            default_for_role=user.role,
        )
        .order_by("-priority", "name")
        .first()
    )
    if role is None:
        return None

    assignment, _created = UserRole.objects.get_or_create(
        user=user,
        role=role,
        defaults={
            "assigned_by": assigned_by,
            "is_active": True,
        },
    )
    if (
        assigned_by is not None
        and assignment.assigned_by_id is None
    ):
        assignment.assigned_by = assigned_by
        assignment.save(update_fields=["assigned_by"])

    user.clear_permission_cache()
    return assignment
