from django import template

from roles.permissions import parse_permission_string

register = template.Library()


def _parse_permissions_csv(permissions_csv):
    permissions = []
    for permission in permissions_csv.split(","):
        permission = permission.strip()
        if not permission:
            continue
        try:
            permissions.append(parse_permission_string(permission))
        except ValueError:
            continue
    return permissions


@register.filter
def has_permission(user, permission_string):
    if not getattr(user, "is_authenticated", False):
        return False
    try:
        module_slug, permission_codename = parse_permission_string(
            permission_string
        )
    except ValueError:
        return False
    return user.has_permission(module_slug, permission_codename)


@register.filter
def has_any_permission(user, permissions_csv):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.has_any_permission(_parse_permissions_csv(permissions_csv))


@register.filter
def has_all_permissions(user, permissions_csv):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.has_all_permissions(_parse_permissions_csv(permissions_csv))


@register.simple_tag
def get_user_permissions(user):
    if not user.is_authenticated:
        return set()
    return user.get_all_permissions()


@register.simple_tag
def get_user_role_names(user):
    if not user.is_authenticated:
        return []
    return user.get_role_names()


@register.filter
def has_role(user, role_name):
    if not user.is_authenticated:
        return False
    return role_name in user.get_role_names()
