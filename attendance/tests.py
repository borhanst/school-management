from django.test import TestCase
from django.urls import reverse

from accounts.models import ParentProfile, TeacherProfile, User
from communications.models import Notice
from students.models import AcademicYear, ClassLevel, Section, Student


class LeaveRequestNoticeViewTests(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date="2025-01-01",
            end_date="2025-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 1",
            numeric_name=1,
        )
        self.section = Section.objects.create(
            name="A",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )

        self.student_user = User.objects.create_user(
            username="student1",
            password="testpass123",
            role="student",
            first_name="Student",
            last_name="One",
        )
        self.student = Student.objects.create(
            user=self.student_user,
            admission_no="ADM001",
            admission_date="2025-01-01",
            date_of_birth="2010-01-01",
            gender="male",
            class_level=self.class_level,
            section=self.section,
            academic_year=self.academic_year,
        )

        self.parent_user = User.objects.create_user(
            username="parent1",
            password="testpass123",
            role="parent",
        )
        self.parent_profile = ParentProfile.objects.get(user=self.parent_user)
        self.parent_profile.children.add(self.student)

        self.teacher_user = User.objects.create_user(
            username="teacher1",
            password="testpass123",
            role="teacher",
            first_name="Teacher",
            last_name="One",
        )
        self.teacher_user.is_superuser = True
        self.teacher_user.save()
        self.teacher_profile = TeacherProfile.objects.get(
            user=self.teacher_user
        )

    def test_leave_request_create_creates_notice(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(
            reverse("attendance:leave_request_add"),
            {
                "student": self.student.id,
                "from_date": "2025-02-01",
                "to_date": "2025-02-03",
                "reason": "Medical",
            },
        )

        self.assertRedirects(response, reverse("attendance:leave_requests"))
        self.assertEqual(Notice.objects.count(), 1)
        notice = Notice.objects.get()
        self.assertEqual(notice.title, "Leave request submitted")
        self.assertEqual(notice.for_roles, ["admin", "teacher"])
        self.assertEqual(list(notice.for_classes.all()), [self.class_level])

    def test_leave_request_approve_creates_notice(self):
        leave_request = self.student.leave_requests.create(
            from_date="2025-02-01",
            to_date="2025-02-03",
            reason="Medical",
            academic_year=self.academic_year,
        )
        self.client.force_login(self.teacher_user)

        response = self.client.post(
            reverse(
                "attendance:leave_request_approve",
                kwargs={"pk": leave_request.id},
            ),
            {"remarks": "Approved"},
        )

        leave_request.refresh_from_db()

        self.assertRedirects(response, reverse("attendance:leave_requests"))
        self.assertEqual(leave_request.status, "approved")
        self.assertEqual(Notice.objects.count(), 1)
        notice = Notice.objects.get()
        self.assertEqual(notice.title, "Leave request approved")
        self.assertEqual(notice.for_roles, ["student", "parent"])

    def test_leave_request_reject_creates_notice(self):
        leave_request = self.student.leave_requests.create(
            from_date="2025-02-01",
            to_date="2025-02-03",
            reason="Medical",
            academic_year=self.academic_year,
        )
        self.client.force_login(self.teacher_user)

        response = self.client.post(
            reverse(
                "attendance:leave_request_reject",
                kwargs={"pk": leave_request.id},
            ),
            {"remarks": "Rejected"},
        )

        leave_request.refresh_from_db()

        self.assertRedirects(response, reverse("attendance:leave_requests"))
        self.assertEqual(leave_request.status, "rejected")
        self.assertEqual(Notice.objects.count(), 1)
        notice = Notice.objects.get()
        self.assertEqual(notice.title, "Leave request rejected")
        self.assertEqual(notice.for_roles, ["student", "parent"])

    def test_leave_request_get_does_not_create_notice(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse("attendance:leave_request_add"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notice.objects.count(), 0)

    def test_leave_request_missing_student_does_not_create_notice(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(
            reverse("attendance:leave_request_add"),
            {
                "from_date": "2025-02-01",
                "to_date": "2025-02-03",
                "reason": "Medical",
            },
        )

        self.assertRedirects(response, reverse("attendance:leave_requests"))
        self.assertEqual(Notice.objects.count(), 0)

    def test_parent_can_update_pending_leave_request(self):
        leave_request = self.student.leave_requests.create(
            from_date="2025-02-01",
            to_date="2025-02-03",
            reason="Medical",
            academic_year=self.academic_year,
        )
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse(
                "attendance:leave_request_edit",
                kwargs={"pk": leave_request.id},
            ),
            {
                "student": self.student.id,
                "from_date": "2025-02-05",
                "to_date": "2025-02-06",
                "reason": "Family event",
            },
        )

        leave_request.refresh_from_db()

        self.assertRedirects(response, reverse("attendance:leave_requests"))
        self.assertEqual(str(leave_request.from_date), "2025-02-05")
        self.assertEqual(str(leave_request.to_date), "2025-02-06")
        self.assertEqual(leave_request.reason, "Family event")

    def test_parent_can_delete_pending_leave_request(self):
        leave_request = self.student.leave_requests.create(
            from_date="2025-02-01",
            to_date="2025-02-03",
            reason="Medical",
            academic_year=self.academic_year,
        )
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse(
                "attendance:leave_request_delete",
                kwargs={"pk": leave_request.id},
            )
        )

        self.assertRedirects(response, reverse("attendance:leave_requests"))
        self.assertFalse(
            self.student.leave_requests.filter(id=leave_request.id).exists()
        )

    def test_parent_cannot_update_approved_leave_request(self):
        leave_request = self.student.leave_requests.create(
            from_date="2025-02-01",
            to_date="2025-02-03",
            reason="Medical",
            academic_year=self.academic_year,
            status="approved",
        )
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse(
                "attendance:leave_request_edit",
                kwargs={"pk": leave_request.id},
            ),
            {
                "student": self.student.id,
                "from_date": "2025-02-05",
                "to_date": "2025-02-06",
                "reason": "Family event",
            },
        )

        leave_request.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(str(leave_request.from_date), "2025-02-01")
        self.assertEqual(leave_request.reason, "Medical")

    def test_parent_cannot_delete_approved_leave_request(self):
        leave_request = self.student.leave_requests.create(
            from_date="2025-02-01",
            to_date="2025-02-03",
            reason="Medical",
            academic_year=self.academic_year,
            status="approved",
        )
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse(
                "attendance:leave_request_delete",
                kwargs={"pk": leave_request.id},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            self.student.leave_requests.filter(id=leave_request.id).exists()
        )
