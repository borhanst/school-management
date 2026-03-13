from django import template

from roles.permissions import parse_permission_string

register = template.Library()


@register.filter
def has_permission(user, permission_string):
    """
    Check if user has a specific permission.
    Usage: {% if user|has_permission:'module.action' %}
    """
    if not user.is_authenticated:
        return False

    try:
        module, action = parse_permission_string(permission_string)
        return user.has_permission(module, action)
    except (ValueError, AttributeError):
        return False


@register.filter
def has_any_permission(user, permissions_csv):
    """
    Check if user has ANY of the specified permissions.
    Usage: {% if user|has_any_permission:'module1.action1,module2.action2' %}
    """
    if not user.is_authenticated:
        return False

    try:
        perms_list = [
            parse_permission_string(permission)
            for permission in permissions_csv.split(",")
            if permission.strip()
        ]
        return user.has_any_permission(perms_list)
    except (ValueError, AttributeError):
        return False


@register.filter
def has_all_permissions(user, permissions_csv):
    """
    Check if user has ALL of the specified permissions.
    Usage: {% if user|has_all_permissions:'module1.action1,module2.action2' %}
    """
    if not user.is_authenticated:
        return False

    try:
        perms_list = [
            parse_permission_string(permission)
            for permission in permissions_csv.split(",")
            if permission.strip()
        ]
        return user.has_all_permissions(perms_list)
    except (ValueError, AttributeError):
        return False


@register.simple_tag
def get_user_permissions(user):
    """
    Get all permissions for the user.
    Usage: {% get_user_permissions user as perms %}
    """
    if not user.is_authenticated:
        return set()
    return user.get_all_permissions()


@register.simple_tag
def get_user_role_names(user):
    """
    Get role names for the user.
    Usage: {% get_user_role_names user as roles %}
    """
    if not user.is_authenticated:
        return []
    return user.get_role_names()


@register.filter
def has_role(user, role_name):
    """
    Check if user has a specific role.
    Usage: {% if user|has_role:'admin' %}
    """
    if not user.is_authenticated:
        return False
    return role_name in user.get_role_names()
