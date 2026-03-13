"""Signal handlers for permission cache invalidation."""

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import Module, PermissionType, Role, RolePermission, UserRole


def _clear_user_permission_cache(user_ids):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for user in User.objects.filter(id__in=set(user_ids)):
        user.clear_permission_cache()


@receiver(post_save, sender=UserRole)
@receiver(post_delete, sender=UserRole)
def clear_cache_for_user_role_change(sender, instance, **kwargs):
    instance.user.clear_permission_cache()


@receiver(post_save, sender=Role)
def clear_cache_for_role_change(sender, instance, **kwargs):
    user_ids = instance.user_assignments.values_list("user_id", flat=True)
    _clear_user_permission_cache(user_ids)


@receiver(m2m_changed, sender=Role.permissions.through)
def clear_cache_for_role_permission_change(sender, instance, action, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    user_ids = instance.user_assignments.values_list("user_id", flat=True)
    _clear_user_permission_cache(user_ids)


@receiver(post_save, sender=Module)
@receiver(post_delete, sender=Module)
def clear_cache_for_module_change(sender, instance, **kwargs):
    user_ids = UserRole.objects.filter(
        role__permissions__module=instance,
        is_active=True,
        role__is_active=True,
    ).values_list("user_id", flat=True)
    _clear_user_permission_cache(user_ids)


@receiver(post_save, sender=PermissionType)
@receiver(post_delete, sender=PermissionType)
@receiver(post_save, sender=RolePermission)
@receiver(post_delete, sender=RolePermission)
def clear_cache_for_permission_metadata_change(sender, instance, **kwargs):
    if isinstance(instance, PermissionType):
        role_permissions = RolePermission.objects.filter(permission_type=instance)
    elif isinstance(instance, RolePermission):
        role_permissions = RolePermission.objects.filter(pk=instance.pk)
    else:
        role_permissions = RolePermission.objects.none()

    user_ids = UserRole.objects.filter(
        role__permissions__in=role_permissions,
        is_active=True,
        role__is_active=True,
    ).values_list("user_id", flat=True)
    _clear_user_permission_cache(user_ids)
