"""
Utility functions for efficient permission queries.
Use these for admin interfaces and bulk operations.
"""

from django.db.models import Q

from roles.permissions import build_permission_key, has_permission_key
from roles.models import RolePermission, UserRole


def get_user_permissions_from_db(user):
    """
    Efficiently get user permissions using optimized queries.
    Useful for admin interfaces and bulk operations.

    Args:
        user: User instance or user ID

    Returns:
        set: Permission strings like {'students_view', 'fees_add'}
    """
    user_id = user.id if hasattr(user, "id") else user

    # Single optimized query using values_list
    permissions = (
        RolePermission.objects.filter(
            role__user_assignments__user_id=user_id,
            role__user_assignments__is_active=True,
            role__user_assignments__role__is_active=True,
            role__is_active=True,
            module__is_active=True,
        )
        .filter(
            Q(role__user_assignments__expires_at__isnull=True)
            | Q(role__user_assignments__expires_at__gte=timezone.now())
        )
        .values_list("module__slug", "permission_type__codename")
        .distinct()
    )

    return {build_permission_key(m[0], m[1]) for m in permissions}


def check_permission_efficient(user, module_slug, action):
    """
    Check permission using database query (no caching).
    Use when you need real-time accuracy.

    Args:
        user: User instance
        module_slug: Module identifier
        action: Permission action

    Returns:
        bool: True if user has permission
    """
    if user.is_superuser:
        return True

    if not user.is_active:
        return False

    return RolePermission.objects.filter(
        role__user_assignments__user=user,
        role__user_assignments__is_active=True,
        role__user_assignments__role__is_active=True,
        role__is_active=True,
        module__slug=module_slug,
        module__is_active=True,
        permission_type__codename=action,
    ).filter(
        Q(role__user_assignments__expires_at__isnull=True)
        | Q(role__user_assignments__expires_at__gte=timezone.now())
    ).exists()


def get_users_with_permission(module_slug, action):
    """
    Get all users who have a specific permission.
    Useful for admin listing and notifications.

    Args:
        module_slug: Module identifier
        action: Permission action

    Returns:
        QuerySet: User objects with the permission
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user_ids = (
        UserRole.objects.filter(
            role__permissions__module__slug=module_slug,
            role__permissions__permission_type__codename=action,
            is_active=True,
            role__is_active=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now()))
        .values_list("user_id", flat=True)
        .distinct()
    )

    return User.objects.filter(id__in=user_ids, is_active=True)


def get_users_with_role(role_name):
    """
    Get all users who have a specific role.

    Args:
        role_name: Name of the role

    Returns:
        QuerySet: User objects with the role
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    return (
        User.objects.filter(
            user_roles__role__name=role_name,
            user_roles__is_active=True,
            user_roles__role__is_active=True,
        )
        .filter(
            Q(user_roles__expires_at__isnull=True)
            | Q(user_roles__expires_at__gte=timezone.now())
        )
        .distinct()
    )


def get_permission_matrix():
    """
    Get a complete permission matrix of all roles and their permissions.

    Returns:
        dict: {role_name: {module_slug: [actions]}}
    """
    from roles.models import Role

    matrix = {}

    for role in Role.objects.filter(is_active=True).prefetch_related(
        "permissions__module", "permissions__permission_type"
    ):
        matrix[role.name] = {}
        for perm in role.permissions.all():
            module = perm.module.slug
            action = perm.permission_type.codename
            if module not in matrix[role.name]:
                matrix[role.name][module] = []
            matrix[role.name][module].append(action)

    return matrix


def bulk_check_permissions(user, permissions_list):
    """
    Check multiple permissions at once efficiently.

    Args:
        user: User instance
        permissions_list: List of tuples [(module_slug, action), ...]

    Returns:
        dict: {(module_slug, action): bool}
    """
    if user.is_superuser:
        return {perm: True for perm in permissions_list}

    user_perms = user.get_all_permissions()
    return {
        (module, action): has_permission_key(user_perms, module, action)
        for module, action in permissions_list
    }


# Import timezone for expiry check
from django.utils import timezone
