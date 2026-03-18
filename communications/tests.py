from unittest.mock import patch

from django.test import TestCase
from django.test import RequestFactory
from django.urls import reverse
from django.views import View

from accounts.models import ParentProfile
from accounts.models import User
from students.models import AcademicYear, ClassLevel, Student

from .mixins import NoticeCreateMixin
from .models import Notice
from .services import create_notice


class CreateNoticeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin1",
            password="testpass123",
            role="admin",
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 1",
            numeric_name=1,
        )
        AcademicYear.objects.create(
            name="2025-2026",
            start_date="2025-01-01",
            end_date="2025-12-31",
            is_current=True,
        )

    def test_create_notice_uses_defaults(self):
        notice = create_notice(
            title="General notice",
            content="Test content",
            posted_by=self.user,
        )

        self.assertEqual(notice.title, "General notice")
        self.assertEqual(notice.content, "Test content")
        self.assertEqual(notice.notice_type, "general")
        self.assertEqual(notice.posted_by, self.user)
        self.assertEqual(notice.for_roles, [])
        self.assertIsNotNone(notice.publish_date)
        self.assertTrue(notice.is_active)
        self.assertFalse(notice.is_pinned)

    def test_create_notice_normalizes_single_role_and_assigns_classes(self):
        notice = create_notice(
            title="Class update",
            content="Important update",
            posted_by=self.user,
            notice_type="academic",
            for_roles="student",
            for_classes=[self.class_level.id],
            is_pinned=True,
        )

        self.assertEqual(notice.for_roles, ["student"])
        self.assertEqual(list(notice.for_classes.all()), [self.class_level])
        self.assertTrue(notice.is_pinned)


class DummyNoticeView(NoticeCreateMixin, View):
    def get_notice_title(self):
        return "Dummy title"

    def get_notice_content(self):
        return "Dummy content"

    def get_notice_roles(self):
        return ["teacher"]

    def get_notice_classes(self):
        return [self.class_level.id]


class NoticeCreateMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="teacher1",
            password="testpass123",
            role="teacher",
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 2",
            numeric_name=2,
        )

    def test_create_notice_from_request_uses_view_methods(self):
        request = self.factory.post("/communications/notices/")
        request.user = self.user

        view = DummyNoticeView()
        view.request = request
        view.class_level = self.class_level

        notice = view.create_notice_from_request()

        self.assertEqual(Notice.objects.count(), 1)
        self.assertEqual(notice.title, "Dummy title")
        self.assertEqual(notice.content, "Dummy content")
        self.assertEqual(notice.posted_by, self.user)
        self.assertEqual(notice.for_roles, ["teacher"])
        self.assertEqual(list(notice.for_classes.all()), [self.class_level])


@patch("communications.views.is_module_active", return_value=True)
@patch("accounts.models.User.has_permission", return_value=True)
class NoticeListViewTests(TestCase):
    def setUp(self):
        self.class_level = ClassLevel.objects.create(
            name="Class 3",
            numeric_name=3,
        )
        self.other_class_level = ClassLevel.objects.create(
            name="Class 4",
            numeric_name=4,
        )
        self.academic_year = AcademicYear.objects.create(
            name="2026-2027",
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_current=True,
        )

    def test_student_only_sees_matching_role_and_class_notices(
        self, mocked_has_permission, mocked_module_active
    ):
        user = User.objects.create_user(
            username="student1",
            password="testpass123",
            role="student",
        )
        Student.objects.create(
            user=user,
            admission_no="ADM-1001",
            admission_date="2026-01-10",
            date_of_birth="2014-05-04",
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.client.force_login(user)

        visible_notice = create_notice(
            title="Fee reminder",
            content="Monthly fee is due this week.",
            notice_type="fee",
            for_roles=["student"],
            for_classes=[self.class_level.id],
        )
        hidden_notice = create_notice(
            title="Other class notice",
            content="This is for another class.",
            for_roles=["student"],
            for_classes=[self.other_class_level.id],
        )
        create_notice(
            title="Teachers only",
            content="Staff meeting reminder.",
            for_roles=["teacher"],
        )

        response = self.client.get(reverse("communications:notices"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible_notice.title)
        self.assertNotContains(response, hidden_notice.title)
        self.assertEqual(list(response.context["notices"]), [visible_notice])

    def test_parent_sees_notice_for_child_class(
        self, mocked_has_permission, mocked_module_active
    ):
        parent_user = User.objects.create_user(
            username="parent1",
            password="testpass123",
            role="parent",
        )
        parent_profile = ParentProfile.objects.get(user=parent_user)

        student_user = User.objects.create_user(
            username="child1",
            password="testpass123",
            role="student",
        )
        student = Student.objects.create(
            user=student_user,
            admission_no="ADM-1002",
            admission_date="2026-01-10",
            date_of_birth="2013-08-14",
            gender="female",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        parent_profile.children.add(student)
        self.client.force_login(parent_user)

        visible_notice = create_notice(
            title="Parent fee update",
            content="Fee counter will close early on Friday.",
            notice_type="fee",
            for_roles=["parent"],
            for_classes=[self.class_level.id],
        )
        create_notice(
            title="Different class parent notice",
            content="Only for another class.",
            for_roles=["parent"],
            for_classes=[self.other_class_level.id],
        )

        response = self.client.get(reverse("communications:notices"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible_notice.title)
        self.assertEqual(list(response.context["notices"]), [visible_notice])
