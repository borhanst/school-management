from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import (
    SchoolInfo, AcademicSetting, GradingSetting, GradeScale,
    AttendanceSetting, ExaminationSetting, ExamTypeConfig,
    PromotionSetting, StudentSetting, FeeSetting,
    LibrarySetting, TransportSetting, ReportCardSetting,
    get_school_info, get_academic_setting, get_grading_setting,
)
from students.models import AcademicYear

User = get_user_model()


class AcademicYearViewTests(TestCase):
    """Tests for academic year management views."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.force_login(self.user)
    
    def test_academic_year_list_view(self):
        """Test academic year list view loads."""
        response = self.client.get(reverse('settings:academic-year-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'settings/academic_year_list.html')
    
    def test_academic_year_create_view_get(self):
        """Test academic year create form loads."""
        response = self.client.get(reverse('settings:academic-year-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'settings/academic_year_form.html')
    
    def test_academic_year_create_view_post(self):
        """Test creating an academic year."""
        response = self.client.post(reverse('settings:academic-year-create'), {
            'name': '2024-2025',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'is_current': True,
            'is_active': True,
        })
        self.assertEqual(AcademicYear.objects.count(), 1)
        year = AcademicYear.objects.first()
        self.assertEqual(year.name, '2024-2025')
        self.assertTrue(year.is_current)
        self.assertRedirects(response, reverse('settings:academic-year-list'))
    
    def test_academic_year_edit_view(self):
        """Test editing an academic year."""
        year = AcademicYear.objects.create(
            name='2023-2024',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        response = self.client.post(reverse('settings:academic-year-edit', args=[year.pk]), {
            'name': '2023-2024 Updated',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'is_current': False,
            'is_active': True,
        })
        year.refresh_from_db()
        self.assertEqual(year.name, '2023-2024 Updated')
        self.assertRedirects(response, reverse('settings:academic-year-list'))
    
    def test_academic_year_delete_view(self):
        """Test deleting an academic year."""
        year = AcademicYear.objects.create(
            name='2022-2023',
            start_date='2022-01-01',
            end_date='2022-12-31'
        )
        response = self.client.post(reverse('settings:academic-year-delete', args=[year.pk]))
        self.assertFalse(AcademicYear.objects.filter(pk=year.pk).exists())
        self.assertRedirects(response, reverse('settings:academic-year-list'))
    
    def test_cannot_delete_current_year(self):
        """Test that current academic year cannot be deleted."""
        year = AcademicYear.objects.create(
            name='2024-2025',
            start_date='2024-01-01',
            end_date='2024-12-31',
            is_current=True
        )
        response = self.client.post(reverse('settings:academic-year-delete', args=[year.pk]))
        self.assertTrue(AcademicYear.objects.filter(pk=year.pk).exists())
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), "Cannot delete the current academic year.")
    
    def test_only_one_current_year(self):
        """Test that only one academic year can be current."""
        year1 = AcademicYear.objects.create(
            name='2023-2024',
            start_date='2023-01-01',
            end_date='2023-12-31',
            is_current=True
        )
        year2 = AcademicYear.objects.create(
            name='2024-2025',
            start_date='2024-01-01',
            end_date='2024-12-31',
            is_current=True
        )
        year1.refresh_from_db()
        self.assertFalse(year1.is_current)
        self.assertTrue(year2.is_current)


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
