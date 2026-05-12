from roles.permissions import is_module_active
from roles.models import Module


def is_fee_module_active():
    if not Module.objects.filter(slug="fees").exists():
        return True
    return is_module_active("fees")


def is_parent_fee_user(user):
    return user.role == "parent" and hasattr(user, "parent_profile")


def is_student_fee_user(user):
    return user.role == "student" and hasattr(user, "student_profile")


def can_manage_fee_settings(user):
    if not is_fee_module_active():
        return False
    return user.is_superuser or user.role == "admin" or user.has_permission(
        "fees", "manage_fee"
    )


def can_access_fee_portal(user):
    if not is_fee_module_active():
        return False

    return (
        can_manage_fee_settings(user)
        or is_parent_fee_user(user)
        or is_student_fee_user(user)
        or user.has_permission("fees", "view")
    )


def can_collect_fee_payment(user):
    if not is_fee_module_active():
        return False

    return (
        can_manage_fee_settings(user)
        or is_parent_fee_user(user)
        or user.has_permission("fees", "collect")
    )


def filter_visible_invoices(queryset, user):
    if is_student_fee_user(user):
        return queryset.filter(student=user.student_profile)

    if is_parent_fee_user(user):
        return queryset.filter(student__parents=user.parent_profile).distinct()

    return queryset


def default_payment_remarks(user):
    if is_parent_fee_user(user):
        return "Paid from parent fee portal."
    return "Paid from fee desk."
