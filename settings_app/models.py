import calendar
from datetime import time

from django.db import models


BOARD_CHOICES = [
    ("dhaka", "Dhaka"),
    ("rajshahi", "Rajshahi"),
    ("chittagong", "Chittagong"),
    ("comilla", "Comilla"),
    ("jessore", "Jessore"),
    ("dinajpur", "Dinajpur"),
    ("sylhet", "Sylhet"),
    ("barisal", "Barisal"),
    ("mymensingh", "Mymensingh"),
    ("madrasa", "Madrasa"),
    ("technical", "Technical"),
]

MEDIUM_CHOICES = [
    ("bangla", "Bangla"),
    ("english", "English"),
    ("both", "Both"),
]

SHIFT_CHOICES = [
    ("morning", "Morning"),
    ("day", "Day"),
    ("evening", "Evening"),
]

SCHOOL_TYPE_CHOICES = [
    ("government", "Government"),
    ("non_government", "Non-Government"),
    ("private", "Private"),
    ("semi_government", "Semi-Government"),
]

GENDER_TYPE_CHOICES = [
    ("boys", "Boys"),
    ("girls", "Girls"),
    ("co_educational", "Co-Educational"),
]

CATEGORY_CHOICES = [
    ("general", "General"),
    ("madrasa", "Madrasa"),
    ("technical", "Technical"),
]

MONTH_CHOICES = [(i, calendar.month_name[i]) for i in range(1, 13)]


def get_school_info():
    obj, _ = SchoolInfo.objects.get_or_create(pk=1)
    return obj


def get_academic_setting():
    obj, _ = AcademicSetting.objects.get_or_create(pk=1)
    return obj


def get_grading_setting():
    obj, _ = GradingSetting.objects.get_or_create(pk=1)
    return obj


def get_attendance_setting():
    obj, _ = AttendanceSetting.objects.get_or_create(pk=1)
    return obj


def get_examination_setting():
    obj, _ = ExaminationSetting.objects.get_or_create(pk=1)
    return obj


def get_promotion_setting():
    obj, _ = PromotionSetting.objects.get_or_create(pk=1)
    return obj


def get_student_setting():
    obj, _ = StudentSetting.objects.get_or_create(pk=1)
    return obj


def get_fee_setting():
    obj, _ = FeeSetting.objects.get_or_create(pk=1)
    return obj


def get_library_setting():
    obj, _ = LibrarySetting.objects.get_or_create(pk=1)
    return obj


def get_transport_setting():
    obj, _ = TransportSetting.objects.get_or_create(pk=1)
    return obj


def get_report_card_setting():
    obj, _ = ReportCardSetting.objects.get_or_create(pk=1)
    return obj


class SchoolInfo(models.Model):
    name = models.CharField(max_length=200)
    name_bn = models.CharField(max_length=200, verbose_name="Name (Bangla)")
    short_name = models.CharField(max_length=50, blank=True)
    eiin = models.CharField(max_length=20, verbose_name="EIIN", blank=True)
    board_name = models.CharField(max_length=50, choices=BOARD_CHOICES, default="dhaka")
    medium = models.CharField(max_length=20, choices=MEDIUM_CHOICES, default="bangla")
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default="day")
    school_type = models.CharField(max_length=30, choices=SCHOOL_TYPE_CHOICES, default="non_government")
    gender_type = models.CharField(max_length=20, choices=GENDER_TYPE_CHOICES, default="co_educational")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")

    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="settings/", blank=True)
    established_year = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "settings_school_info"
        verbose_name = "School Information"
        verbose_name_plural = "School Information"

    def __str__(self):
        return self.name


class AcademicSetting(models.Model):
    year_start_month = models.IntegerField(choices=MONTH_CHOICES, default=1)
    year_end_month = models.IntegerField(choices=MONTH_CHOICES, default=12)

    term_structure = models.CharField(
        max_length=20,
        choices=[
            ("two", "Two Terms (Jan-Jun, Jul-Dec)"),
            ("three", "Three Terms"),
        ],
        default="two",
    )

    working_days = models.JSONField(
        default=list,
        help_text="Indices: 0=Sunday ... 6=Saturday",
    )

    school_start_time = models.TimeField(default=time(8, 0))
    school_end_time = models.TimeField(default=time(14, 0))
    period_duration = models.IntegerField(default=45, help_text="Minutes")
    periods_per_day = models.IntegerField(default=7)

    min_class = models.IntegerField(default=1)
    max_class = models.IntegerField(default=12)

    section_naming = models.CharField(
        max_length=20,
        choices=[
            ("alpha", "A, B, C, D"),
            ("numeric", "1, 2, 3"),
        ],
        default="alpha",
    )
    max_sections_per_class = models.IntegerField(default=4)
    max_students_per_section = models.IntegerField(default=50)

    class Meta:
        db_table = "settings_academic"
        verbose_name = "Academic Setting"
        verbose_name_plural = "Academic Settings"

    def __str__(self):
        return "Academic Settings"


class GradingSetting(models.Model):
    gpa_scale = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    pass_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=33.00)
    include_fourth_subject = models.BooleanField(default=True)
    fail_on_compulsory_subject = models.BooleanField(default=True)
    grade_display_format = models.CharField(
        max_length=20,
        choices=[("letter", "Letter"), ("gpa", "GPA"), ("both", "Both")],
        default="both",
    )

    class Meta:
        db_table = "settings_grading"
        verbose_name = "Grading Setting"
        verbose_name_plural = "Grading Settings"

    def __str__(self):
        return "Grading Settings"


class GradeScale(models.Model):
    grading_setting = models.ForeignKey(
        GradingSetting, on_delete=models.CASCADE, related_name="grade_scales"
    )
    letter_grade = models.CharField(max_length=5)
    min_marks = models.DecimalField(max_digits=5, decimal_places=2)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2)
    remarks = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "settings_grade_scale"
        ordering = ["-min_marks"]
        verbose_name = "Grade Scale"
        verbose_name_plural = "Grade Scales"

    def __str__(self):
        return f"{self.letter_grade} ({self.min_marks}-{self.max_marks})"


class AttendanceSetting(models.Model):
    minimum_attendance_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=70.00
    )
    late_threshold_minutes = models.IntegerField(default=10)
    attendance_types = models.JSONField(
        default=list,
        help_text="['present', 'absent', 'late', 'leave']",
    )

    class Meta:
        db_table = "settings_attendance"
        verbose_name = "Attendance Setting"
        verbose_name_plural = "Attendance Settings"

    def __str__(self):
        return "Attendance Settings"


class ExaminationSetting(models.Model):
    mark_distribution_type = models.CharField(
        max_length=20,
        choices=[
            ("board", "Board Pattern (MCQ + Written)"),
            ("custom", "Custom"),
        ],
        default="board",
    )
    total_marks_per_subject = models.IntegerField(default=100)
    board_exam_classes = models.JSONField(
        default=list,
        help_text="[10, 12] - Classes with board exams (SSC/HSC)",
    )

    class Meta:
        db_table = "settings_examination"
        verbose_name = "Examination Setting"
        verbose_name_plural = "Examination Settings"

    def __str__(self):
        return "Examination Settings"


class ExamTypeConfig(models.Model):
    name = models.CharField(max_length=100)
    name_bn = models.CharField(max_length=100, blank=True)
    weightage = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.IntegerField(default=100)
    pass_marks = models.IntegerField(default=33)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_exam_type_config"
        ordering = ["weightage"]
        verbose_name = "Exam Type Config"
        verbose_name_plural = "Exam Type Configs"

    def __str__(self):
        return self.name


class PromotionSetting(models.Model):
    auto_promote = models.BooleanField(default=False)
    minimum_gpa_for_promotion = models.DecimalField(max_digits=3, decimal_places=2, default=2.00)
    max_failed_subjects = models.IntegerField(default=0)
    allow_supplementary_exam = models.BooleanField(default=True)
    supplementary_pass_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=33.00)
    require_attendance_for_promotion = models.BooleanField(default=True)
    promotion_month = models.IntegerField(choices=MONTH_CHOICES, default=1)

    class Meta:
        db_table = "settings_promotion"
        verbose_name = "Promotion Setting"
        verbose_name_plural = "Promotion Settings"

    def __str__(self):
        return "Promotion Settings"


class StudentSetting(models.Model):
    admission_no_prefix = models.CharField(max_length=10, default="ADM")
    admission_no_format = models.CharField(max_length=50, default="{prefix}-{year}-{seq}")
    admission_no_sequence_length = models.IntegerField(default=4)
    photo_required = models.BooleanField(default=True)
    blood_group_required = models.BooleanField(default=False)
    religion_required = models.BooleanField(default=True)
    birth_certificate_required = models.BooleanField(default=True)
    track_previous_school = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_student"
        verbose_name = "Student Setting"
        verbose_name_plural = "Student Settings"

    def __str__(self):
        return "Student Settings"


class FeeSetting(models.Model):
    currency_symbol = models.CharField(max_length=5, default="৳")
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_grace_days = models.IntegerField(default=10)
    max_late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    receipt_prefix = models.CharField(max_length=10, default="RCP")
    allow_partial_payment = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_fee"
        verbose_name = "Fee Setting"
        verbose_name_plural = "Fee Settings"

    def __str__(self):
        return "Fee Settings"


class LibrarySetting(models.Model):
    max_books_per_student = models.IntegerField(default=3)
    max_books_per_teacher = models.IntegerField(default=5)
    issue_duration_days = models.IntegerField(default=14)
    fine_per_day = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    max_fine = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    renewal_allowed = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_library"
        verbose_name = "Library Setting"
        verbose_name_plural = "Library Settings"

    def __str__(self):
        return "Library Settings"


class TransportSetting(models.Model):
    fare_calculation_type = models.CharField(
        max_length=20,
        choices=[("distance", "Distance"), ("route", "Route"), ("flat", "Flat")],
        default="route",
    )
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "settings_transport"
        verbose_name = "Transport Setting"
        verbose_name_plural = "Transport Settings"

    def __str__(self):
        return "Transport Settings"


class ReportCardSetting(models.Model):
    show_attendance = models.BooleanField(default=True)
    show_teacher_remarks = models.BooleanField(default=True)
    show_class_rank = models.BooleanField(default=False)
    show_gpa = models.BooleanField(default=True)
    show_fourth_subject_bonus = models.BooleanField(default=True)
    show_school_logo = models.BooleanField(default=True)
    show_board_name = models.BooleanField(default=True)
    signature_fields = models.JSONField(
        default=list,
        help_text="['head_teacher', 'class_teacher', 'parent']",
    )

    class Meta:
        db_table = "settings_report_card"
        verbose_name = "Report Card Setting"
        verbose_name_plural = "Report Card Settings"

    def __str__(self):
        return "Report Card Settings"
