from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from dashboard.models import SystemSettings


class SettingsViewTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="pass12345",
            role="admin",
        )
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="pass12345",
            role="teacher",
        )
        SystemSettings.objects.create(
            key="school_name",
            value="Springfield High",
            category="general",
            is_public=True,
        )

    def test_admin_can_access_settings_page(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("accounts:settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Settings")
        self.assertContains(response, "school_name")

    def test_non_admin_cannot_access_settings_page(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse("accounts:settings"))

        self.assertEqual(response.status_code, 403)

    def test_settings_link_hidden_from_non_admin_users(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse("accounts:profile"))

        self.assertNotContains(response, reverse("accounts:settings"))

    def test_settings_link_visible_to_admin_users(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("accounts:profile"))

        self.assertContains(response, reverse("accounts:settings"))
