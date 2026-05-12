from datetime import date

from django.test import TestCase

from accounts.models import TeacherProfile, User
from academics.views import get_user_timetable_sections
from attendance.models import TeacherAttendancePermission
from students.models import AcademicYear, ClassLevel, Section


class TeacherSectionAccessTests(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 4",
            numeric_name=4,
        )
        self.section_a = Section.objects.create(
            name="A",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.section_b = Section.objects.create(
            name="B",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.teacher_user = User.objects.create_user(
            username="teacher_access",
            password="pass12345",
            role="teacher",
        )
        self.teacher_profile = TeacherProfile.objects.get(user=self.teacher_user)

    def test_teacher_timetable_sections_follow_attendance_access(self):
        TeacherAttendancePermission.objects.create(
            teacher=self.teacher_profile,
            section=self.section_a,
            academic_year=self.academic_year,
        )

        sections = get_user_timetable_sections(
            self.teacher_user,
            self.academic_year,
        )

        self.assertEqual(
            list(sections.order_by("id").values_list("id", flat=True)),
            [self.section_a.id],
        )
