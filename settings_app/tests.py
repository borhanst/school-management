from django.test import TestCase
from .models import (
    SchoolInfo, AcademicSetting, GradingSetting, GradeScale,
    AttendanceSetting, ExaminationSetting, ExamTypeConfig,
    PromotionSetting, StudentSetting, FeeSetting,
    LibrarySetting, TransportSetting, ReportCardSetting,
    get_school_info, get_academic_setting, get_grading_setting,
)


class SingletonHelperTests(TestCase):
    def test_get_school_info_creates_if_missing(self):
        info = get_school_info()
        self.assertIsInstance(info, SchoolInfo)
        self.assertEqual(info.pk, 1)

    def test_get_school_info_returns_existing(self):
        info1 = get_school_info()
        info1.name = "Test School"
        info1.save()
        info2 = get_school_info()
        self.assertEqual(info2.name, "Test School")

    def test_get_academic_setting_creates_if_missing(self):
        setting = get_academic_setting()
        self.assertIsInstance(setting, AcademicSetting)

    def test_get_grading_setting_creates_if_missing(self):
        setting = get_grading_setting()
        self.assertIsInstance(setting, GradingSetting)


class SchoolInfoModelTests(TestCase):
    def test_str(self):
        info = SchoolInfo.objects.create(name="Test School", name_bn="টেস্ট স্কুল")
        self.assertEqual(str(info), "Test School")


class AcademicSettingModelTests(TestCase):
    def test_str(self):
        setting = AcademicSetting.objects.create()
        self.assertEqual(str(setting), "Academic Settings")


class GradingSettingModelTests(TestCase):
    def test_str(self):
        setting = GradingSetting.objects.create()
        self.assertEqual(str(setting), "Grading Settings")

    def test_grade_scale_str(self):
        setting = GradingSetting.objects.create()
        scale = GradeScale.objects.create(
            grading_setting=setting,
            letter_grade="A+",
            min_marks=80,
            max_marks=100,
            grade_point=5.00,
        )
        self.assertEqual(str(scale), "A+ (80-100)")


class AttendanceSettingModelTests(TestCase):
    def test_str(self):
        setting = AttendanceSetting.objects.create()
        self.assertEqual(str(setting), "Attendance Settings")


class ExaminationSettingModelTests(TestCase):
    def test_str(self):
        setting = ExaminationSetting.objects.create()
        self.assertEqual(str(setting), "Examination Settings")

    def test_exam_type_config_str(self):
        config = ExamTypeConfig.objects.create(name="Annual", weightage=40)
        self.assertEqual(str(config), "Annual")


class PromotionSettingModelTests(TestCase):
    def test_str(self):
        setting = PromotionSetting.objects.create()
        self.assertEqual(str(setting), "Promotion Settings")


class StudentSettingModelTests(TestCase):
    def test_str(self):
        setting = StudentSetting.objects.create()
        self.assertEqual(str(setting), "Student Settings")


class FeeSettingModelTests(TestCase):
    def test_str(self):
        setting = FeeSetting.objects.create()
        self.assertEqual(str(setting), "Fee Settings")


class LibrarySettingModelTests(TestCase):
    def test_str(self):
        setting = LibrarySetting.objects.create()
        self.assertEqual(str(setting), "Library Settings")


class TransportSettingModelTests(TestCase):
    def test_str(self):
        setting = TransportSetting.objects.create()
        self.assertEqual(str(setting), "Transport Settings")


class ReportCardSettingModelTests(TestCase):
    def test_str(self):
        setting = ReportCardSetting.objects.create()
        self.assertEqual(str(setting), "Report Card Settings")
