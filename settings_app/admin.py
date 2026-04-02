from django.contrib import admin
from .models import (
    SchoolInfo, AcademicSetting, GradingSetting, GradeScale,
    AttendanceSetting, ExaminationSetting, ExamTypeConfig,
    PromotionSetting, StudentSetting, FeeSetting,
    LibrarySetting, TransportSetting, ReportCardSetting,
)


class GradeScaleInline(admin.TabularInline):
    model = GradeScale
    extra = 0


@admin.register(SchoolInfo)
class SchoolInfoAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Basic Info", {"fields": ("name", "name_bn", "short_name", "eiin", "logo")}),
        ("Affiliation", {"fields": ("board_name", "medium", "shift", "school_type", "gender_type", "category")}),
        ("Contact", {"fields": ("address", "phone", "email", "website")}),
        ("Other", {"fields": ("established_year",)}),
    )


@admin.register(AcademicSetting)
class AcademicSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Academic Year", {"fields": ("year_start_month", "year_end_month", "term_structure")}),
        ("Schedule", {"fields": ("school_start_time", "school_end_time", "period_duration", "periods_per_day")}),
        ("Classes", {"fields": ("min_class", "max_class", "section_naming", "max_sections_per_class", "max_students_per_section")}),
    )


@admin.register(GradingSetting)
class GradingSettingAdmin(admin.ModelAdmin):
    inlines = [GradeScaleInline]


@admin.register(AttendanceSetting)
class AttendanceSettingAdmin(admin.ModelAdmin):
    pass


@admin.register(ExaminationSetting)
class ExaminationSettingAdmin(admin.ModelAdmin):
    pass


@admin.register(ExamTypeConfig)
class ExamTypeConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "weightage", "total_marks", "pass_marks", "is_active")


@admin.register(PromotionSetting)
class PromotionSettingAdmin(admin.ModelAdmin):
    pass


@admin.register(StudentSetting)
class StudentSettingAdmin(admin.ModelAdmin):
    pass


@admin.register(FeeSetting)
class FeeSettingAdmin(admin.ModelAdmin):
    pass


@admin.register(LibrarySetting)
class LibrarySettingAdmin(admin.ModelAdmin):
    pass


@admin.register(TransportSetting)
class TransportSettingAdmin(admin.ModelAdmin):
    pass


@admin.register(ReportCardSetting)
class ReportCardSettingAdmin(admin.ModelAdmin):
    pass
