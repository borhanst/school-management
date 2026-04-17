"""Shared helpers for custom permission parsing and evaluation."""

from __future__ import annotations

from typing import Iterable


SUPERUSER_PERMISSION = "*"


def build_permission_key(module_slug: str, permission_codename: str) -> str:
    """Build the canonical internal permission key."""
    return f"{module_slug}_{permission_codename}"


def parse_permission_string(permission_string: str) -> tuple[str, str]:
    """
    Parse a permission string in either ``module.action`` or ``module_action`` form.
    """
    permission_string = permission_string.strip()
    if "." in permission_string:
        module, action = permission_string.split(".", 1)
        return module.strip(), action.strip()

    module, action = permission_string.rsplit("_", 1)
    return module.strip(), action.strip()


def normalize_permission_value(permission: str | tuple[str, str]) -> str:
    """Normalize a permission tuple/string into the canonical internal key."""
    if isinstance(permission, tuple):
        module, action = permission
    else:
        module, action = parse_permission_string(permission)
    return build_permission_key(module, action)


def normalize_permission_set(
    permissions: Iterable[str | tuple[str, str]],
) -> set[str]:
    """Normalize a sequence of permissions into canonical keys."""
    return {normalize_permission_value(permission) for permission in permissions}


def has_permission_key(
    permissions: Iterable[str], module_slug: str, permission_codename: str
) -> bool:
    """Check a canonical permission set for a given module/action pair."""
    permissions = set(permissions)
    return SUPERUSER_PERMISSION in permissions or build_permission_key(
        module_slug, permission_codename
    ) in permissions


def is_module_active(module_slug: str) -> bool:
    """Return whether the named module exists and is active."""
    from roles.models import Module

    return Module.objects.filter(slug=module_slug, is_active=True).exists()


def is_module_inactive(module_slug: str) -> bool:
    """Return whether the named module exists but is disabled."""
    from roles.models import Module

    return Module.objects.filter(slug=module_slug, is_active=False).exists()
