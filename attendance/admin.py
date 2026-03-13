from django.contrib import admin

from .models import (
    Attendance,
    AttendanceSession,
    LeaveRequest,
    TeacherAttendancePermission,
)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "date",
        "status",
        "period",
        "marked_by",
        "academic_year",
    ]
    list_filter = ["status", "date", "academic_year"]
    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "student__admission_no",
    ]
    date_hierarchy = "date"
    ordering = ["-date", "student__roll_number"]


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = [
        "section",
        "date",
        "period",
        "marked_by",
        "is_locked",
        "academic_year",
    ]
    list_filter = ["date", "is_locked", "academic_year"]
    search_fields = ["section__name", "section__class_level__name"]
    date_hierarchy = "date"


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "from_date",
        "to_date",
        "status",
        "approved_by",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "student__admission_no",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]


@admin.register(TeacherAttendancePermission)
class TeacherAttendancePermissionAdmin(admin.ModelAdmin):
    list_display = [
        "teacher",
        "section",
        "academic_year",
        "granted_by",
        "granted_at",
    ]
    list_filter = ["academic_year", "section__class_level"]
    search_fields = [
        "teacher__user__first_name",
        "teacher__user__last_name",
        "teacher__employee_id",
        "section__name",
    ]
    date_hierarchy = "granted_at"
    ordering = ["-granted_at"]
