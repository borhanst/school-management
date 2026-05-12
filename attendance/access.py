from accounts.models import ParentProfile, TeacherProfile
from roles.models import Module
from roles.permissions import is_module_active
from students.access import get_current_academic_year
from students.models import Section


def is_attendance_module_active():
    if not Module.objects.filter(slug="attendance").exists():
        return True
    return is_module_active("attendance")


def get_teacher_allowed_sections(teacher_profile, academic_year):
    if teacher_profile.user.role == "admin":
        return Section.objects.filter(
            academic_year=academic_year,
            is_active=True,
        )

    permissions = teacher_profile.attendance_permissions.filter(
        academic_year=academic_year
    ).values_list("section_id", flat=True)
    return Section.objects.filter(
        id__in=permissions,
        academic_year=academic_year,
        is_active=True,
    )


def get_user_allowed_sections_for_attendance(user, academic_year):
    if academic_year is None:
        return Section.objects.none()

    if getattr(user, "is_superuser", False) or user.role == "admin":
        return Section.objects.filter(
            academic_year=academic_year,
            is_active=True,
        )

    if hasattr(user, "teacher_profile"):
        return get_teacher_allowed_sections(user.teacher_profile, academic_year)

    return Section.objects.none()


def teacher_can_mark_attendance(teacher_profile, section, academic_year):
    if teacher_profile.user.role == "admin":
        return True
    return teacher_profile.attendance_permissions.filter(
        section=section,
        academic_year=academic_year,
    ).exists()


def can_user_mark_attendance_for_section(user, section, academic_year):
    if academic_year is None:
        return False

    if getattr(user, "is_superuser", False) or user.role == "admin":
        return True

    if hasattr(user, "teacher_profile"):
        return teacher_can_mark_attendance(
            user.teacher_profile,
            section,
            academic_year,
        )

    return False


def resolve_attendance_marker(user):
    if hasattr(user, "teacher_profile"):
        return user.teacher_profile
    return None


def parent_can_apply_leave(user):
    return user.role == "parent" and ParentProfile.objects.filter(
        user=user
    ).exists()


def parent_can_view_leave_requests(user):
    return user.role == "parent" and ParentProfile.objects.filter(
        user=user
    ).exists()


def student_can_view_own_leave_requests(user):
    return user.role == "student" and hasattr(user, "student_profile")


def teacher_can_approve_leave(user):
    return user.role in {"admin", "teacher"} and TeacherProfile.objects.filter(
        user=user
    ).exists()
