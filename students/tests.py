from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from accounts.models import User
from attendance.models import Attendance
from students.models import AcademicYear, ClassLevel, Student
from students.summary import build_student_profile_summary


class StudentProfileSummaryTests(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 6",
            numeric_name=6,
        )
        self.user = User.objects.create_user(
            username="student_summary",
            password="pass12345",
            role="student",
        )
        self.student = Student.objects.create(
            user=self.user,
            admission_no="ADM20250011",
            admission_date=date(2025, 1, 5),
            date_of_birth=date(2014, 2, 1),
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )

    def test_summary_without_related_records_returns_safe_defaults(self):
        summary = build_student_profile_summary(
            self.student,
            now=timezone.make_aware(datetime(2025, 2, 5, 10, 30, 0)),
        )

        self.assertEqual(summary["attendance_percentage"], 0)
        self.assertEqual(summary["total_due_amount"], 0)
        self.assertEqual(list(summary["grades"]), [])
        self.assertEqual(list(summary["invoices"]), [])
        self.assertEqual(list(summary["upcoming_exams"]), [])
        self.assertEqual(list(summary["parent_profiles"]), [])
        self.assertEqual(summary["today_timeline"], [])
        self.assertEqual(summary["today_label"], date(2025, 2, 5))


class StudentDeletionRuleTests(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2027-2028",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 5",
            numeric_name=5,
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_delete",
            password="pass12345",
        )

    def _create_student(self, suffix):
        student_user = User.objects.create_user(
            username=f"student_delete_{suffix}",
            password="pass12345",
            role="student",
        )
        return Student.objects.create(
            user=student_user,
            admission_no=f"ADM2027{suffix}",
            admission_date=date(2027, 1, 10),
            date_of_birth=date(2014, 4, 10),
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )

    def test_student_without_history_is_deleted(self):
        student = self._create_student("001")
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse("students:delete", args=[student.id]))

        self.assertRedirects(response, reverse("students:list"))
        self.assertFalse(Student.objects.filter(id=student.id).exists())
        self.assertFalse(User.objects.filter(id=student.user_id).exists())

    def test_student_with_history_is_archived(self):
        student = self._create_student("002")
        Attendance.objects.create(
            student=student,
            date=date(2027, 2, 1),
            status="present",
            academic_year=self.academic_year,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse("students:delete", args=[student.id]))

        self.assertRedirects(response, reverse("students:list"))
        student.refresh_from_db()
        student.user.refresh_from_db()
        self.assertFalse(student.is_active)
        self.assertEqual(student.status, "left")
        self.assertFalse(student.user.is_active)
