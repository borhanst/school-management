import calendar
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from datetime import time

from settings_app.models import (
    SchoolInfo, AcademicSetting, GradingSetting, GradeScale,
    AttendanceSetting, ExaminationSetting, ExamTypeConfig,
    PromotionSetting, StudentSetting, FeeSetting,
    LibrarySetting, TransportSetting, ReportCardSetting,
)
from students.models import AcademicYear


class Command(BaseCommand):
    help = "Seed default settings and academic years for Bangladesh education system"

    def handle(self, *args, **options):
        self.seed_academic_years()
        self.seed_school_info()
        self.seed_academic_setting()
        self.seed_grading_setting()
        self.seed_attendance_setting()
        self.seed_examination_setting()
        self.seed_promotion_setting()
        self.seed_student_setting()
        self.seed_fee_setting()
        self.seed_library_setting()
        self.seed_transport_setting()
        self.seed_report_card_setting()
        self.stdout.write(self.style.SUCCESS("Default settings seeded successfully."))

    def seed_academic_years(self):
        """Seed default academic years."""
        current_year = date.today().year
        
        # Create current academic year
        current_year_obj, created = AcademicYear.objects.get_or_create(
            name=f"{current_year}-{current_year + 1}",
            defaults={
                "start_date": date(current_year, 1, 1),
                "end_date": date(current_year + 1, 12, 31),
                "is_current": True,
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(f"  Created AcademicYear: {current_year_obj.name} (Current)")
        else:
            self.stdout.write(f"  AcademicYear {current_year_obj.name} already exists")

        # Create previous year (inactive)
        prev_year = current_year - 1
        prev_year_obj, created = AcademicYear.objects.get_or_create(
            name=f"{prev_year}-{prev_year + 1}",
            defaults={
                "start_date": date(prev_year, 1, 1),
                "end_date": date(prev_year + 1, 12, 31),
                "is_current": False,
                "is_active": False,
            },
        )
        if created:
            self.stdout.write(f"  Created AcademicYear: {prev_year_obj.name}")
        else:
            self.stdout.write(f"  AcademicYear {prev_year_obj.name} already exists")

    def seed_school_info(self):
        obj, created = SchoolInfo.objects.get_or_create(
            pk=1,
            defaults={
                "name": "Your School Name",
                "name_bn": "আপনার বিদ্যালয়ের নাম",
                "short_name": "School",
                "board_name": "dhaka",
                "medium": "bangla",
                "shift": "day",
                "school_type": "non_government",
                "gender_type": "co_educational",
                "category": "general",
            },
        )
        if created:
            self.stdout.write("  Created SchoolInfo")
        else:
            self.stdout.write("  SchoolInfo already exists")

    def seed_academic_setting(self):
        obj, created = AcademicSetting.objects.get_or_create(
            pk=1,
            defaults={
                "year_start_month": 1,
                "year_end_month": 12,
                "term_structure": "two",
                "working_days": [0, 1, 2, 3, 4, 5],
                "school_start_time": time(8, 0),
                "school_end_time": time(14, 0),
                "period_duration": 45,
                "periods_per_day": 7,
                "min_class": 1,
                "max_class": 12,
                "section_naming": "alpha",
                "max_sections_per_class": 4,
                "max_students_per_section": 50,
            },
        )
        if created:
            self.stdout.write("  Created AcademicSetting")
        else:
            self.stdout.write("  AcademicSetting already exists")

    def seed_grading_setting(self):
        obj, created = GradingSetting.objects.get_or_create(
            pk=1,
            defaults={
                "gpa_scale": Decimal("5.00"),
                "pass_percentage": Decimal("33.00"),
                "include_fourth_subject": True,
                "fail_on_compulsory_subject": True,
                "grade_display_format": "both",
            },
        )
        if created:
            self.stdout.write("  Created GradingSetting")

            grade_scales = [
                ("A+", Decimal("80"), Decimal("100"), Decimal("5.00"), "Outstanding"),
                ("A", Decimal("70"), Decimal("79"), Decimal("4.00"), "Excellent"),
                ("A-", Decimal("60"), Decimal("69"), Decimal("3.50"), "Very Good"),
                ("B", Decimal("50"), Decimal("59"), Decimal("3.00"), "Good"),
                ("C", Decimal("40"), Decimal("49"), Decimal("2.00"), "Satisfactory"),
                ("D", Decimal("33"), Decimal("39"), Decimal("1.00"), "Pass"),
                ("F", Decimal("0"), Decimal("32"), Decimal("0.00"), "Fail"),
            ]
            for letter, min_m, max_m, gp, remarks in grade_scales:
                GradeScale.objects.create(
                    grading_setting=obj,
                    letter_grade=letter,
                    min_marks=min_m,
                    max_marks=max_m,
                    grade_point=gp,
                    remarks=remarks,
                )
            self.stdout.write(f"    Created {len(grade_scales)} GradeScale entries")
        else:
            self.stdout.write("  GradingSetting already exists")

    def seed_attendance_setting(self):
        obj, created = AttendanceSetting.objects.get_or_create(
            pk=1,
            defaults={
                "minimum_attendance_percentage": Decimal("70.00"),
                "late_threshold_minutes": 10,
                "attendance_types": ["present", "absent", "late", "leave"],
            },
        )
        if created:
            self.stdout.write("  Created AttendanceSetting")
        else:
            self.stdout.write("  AttendanceSetting already exists")

    def seed_examination_setting(self):
        obj, created = ExaminationSetting.objects.get_or_create(
            pk=1,
            defaults={
                "mark_distribution_type": "board",
                "total_marks_per_subject": 100,
                "board_exam_classes": [10, 12],
            },
        )
        if created:
            self.stdout.write("  Created ExaminationSetting")

            exam_types = [
                ("Unit Test", "ইউনিট টেস্ট", Decimal("10.00"), 50, 17),
                ("First Term", "প্রথম সাময়িক", Decimal("20.00"), 100, 33),
                ("Half-Yearly", "বার্ষিক অর্ধেক", Decimal("30.00"), 100, 33),
                ("Second Term", "দ্বিতীয় সাময়িক", Decimal("20.00"), 100, 33),
                ("Annual", "বার্ষিক পরীক্ষা", Decimal("40.00"), 100, 33),
            ]
            for name, name_bn, weight, total, pass_m in exam_types:
                ExamTypeConfig.objects.create(
                    name=name,
                    name_bn=name_bn,
                    weightage=weight,
                    total_marks=total,
                    pass_marks=pass_m,
                )
            self.stdout.write(f"    Created {len(exam_types)} ExamTypeConfig entries")
        else:
            self.stdout.write("  ExaminationSetting already exists")

    def seed_promotion_setting(self):
        obj, created = PromotionSetting.objects.get_or_create(
            pk=1,
            defaults={
                "auto_promote": False,
                "minimum_gpa_for_promotion": Decimal("2.00"),
                "max_failed_subjects": 0,
                "allow_supplementary_exam": True,
                "supplementary_pass_percentage": Decimal("33.00"),
                "require_attendance_for_promotion": True,
                "promotion_month": 1,
            },
        )
        if created:
            self.stdout.write("  Created PromotionSetting")
        else:
            self.stdout.write("  PromotionSetting already exists")

    def seed_student_setting(self):
        obj, created = StudentSetting.objects.get_or_create(
            pk=1,
            defaults={
                "admission_no_prefix": "ADM",
                "admission_no_format": "{prefix}-{year}-{seq}",
                "admission_no_sequence_length": 4,
                "photo_required": True,
                "blood_group_required": False,
                "religion_required": True,
                "birth_certificate_required": True,
                "track_previous_school": True,
            },
        )
        if created:
            self.stdout.write("  Created StudentSetting")
        else:
            self.stdout.write("  StudentSetting already exists")

    def seed_fee_setting(self):
        obj, created = FeeSetting.objects.get_or_create(
            pk=1,
            defaults={
                "currency_symbol": "৳",
                "late_fee_per_day": Decimal("0"),
                "late_fee_grace_days": 10,
                "max_late_fee": Decimal("500"),
                "receipt_prefix": "RCP",
                "allow_partial_payment": True,
            },
        )
        if created:
            self.stdout.write("  Created FeeSetting")
        else:
            self.stdout.write("  FeeSetting already exists")

    def seed_library_setting(self):
        obj, created = LibrarySetting.objects.get_or_create(
            pk=1,
            defaults={
                "max_books_per_student": 3,
                "max_books_per_teacher": 5,
                "issue_duration_days": 14,
                "fine_per_day": Decimal("2.00"),
                "max_fine": Decimal("100.00"),
                "renewal_allowed": True,
            },
        )
        if created:
            self.stdout.write("  Created LibrarySetting")
        else:
            self.stdout.write("  LibrarySetting already exists")

    def seed_transport_setting(self):
        obj, created = TransportSetting.objects.get_or_create(
            pk=1,
            defaults={
                "fare_calculation_type": "route",
                "monthly_fee": Decimal("0"),
            },
        )
        if created:
            self.stdout.write("  Created TransportSetting")
        else:
            self.stdout.write("  TransportSetting already exists")

    def seed_report_card_setting(self):
        obj, created = ReportCardSetting.objects.get_or_create(
            pk=1,
            defaults={
                "show_attendance": True,
                "show_teacher_remarks": True,
                "show_class_rank": False,
                "show_gpa": True,
                "show_fourth_subject_bonus": True,
                "show_school_logo": True,
                "show_board_name": True,
                "signature_fields": ["head_teacher", "class_teacher", "parent"],
            },
        )
        if created:
            self.stdout.write("  Created ReportCardSetting")
        else:
            self.stdout.write("  ReportCardSetting already exists")
