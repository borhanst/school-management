from django.contrib import admin

from .models import (
    ExamSchedule,
    ExamType,
    Grade,
    GradeDistribution,
    Term,
)


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "academic_year",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["academic_year", "is_active"]
    search_fields = ["name"]
    ordering = ["-academic_year", "start_date"]


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "academic_year", "weightage", "is_active"]
    list_filter = ["academic_year", "is_active"]
    search_fields = ["name"]
    ordering = ["-academic_year", "name"]


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "exam_type",
        "subject",
        "class_level",
        "academic_year",
        "date",
        "start_time",
        "end_time",
        "marks",
    ]
    list_filter = ["exam_type", "class_level", "academic_year", "date"]
    search_fields = ["subject__name", "class_level__name"]
    ordering = ["-date", "start_time"]
    date_hierarchy = "date"


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "subject",
        "exam_type",
        "marks",
        "grade_letter",
        "academic_year",
    ]
    list_filter = ["exam_type", "academic_year", "grade_letter"]
    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "subject__name",
    ]
    ordering = ["-academic_year", "student"]


@admin.register(GradeDistribution)
class GradeDistributionAdmin(admin.ModelAdmin):
    list_display = [
        "class_level",
        "subject",
        "exam_type",
        "min_marks",
        "max_marks",
        "grade_letter",
    ]
    list_filter = ["class_level", "exam_type", "grade_letter"]
    search_fields = ["subject__name", "class_level__name"]
    ordering = ["class_level", "subject", "min_marks"]
