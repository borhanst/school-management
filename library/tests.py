from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.models import User

from .models import Book, BookCategory


@patch("library.views.is_module_active", return_value=True)
@patch("accounts.models.User.has_permission", return_value=True)
class LibraryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="librarian1",
            password="testpass123",
            role="teacher",
        )
        self.category = BookCategory.objects.create(
            name="Science",
            code="SCI",
        )
        Book.objects.create(
            isbn="9780000000001",
            title="Physics Fundamentals",
            author="A. Author",
            category=self.category,
            quantity=5,
            available=3,
        )
        Book.objects.create(
            isbn="9780000000002",
            title="History Atlas",
            author="B. Writer",
            quantity=2,
            available=0,
        )

    def test_books_page_renders_catalog(
        self, mocked_has_permission, mocked_module_active
    ):
        self.client.force_login(self.user)

        response = self.client.get(reverse("library:books"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Library")
        self.assertContains(response, "Physics Fundamentals")
        self.assertContains(response, "History Atlas")

    def test_books_page_filters_by_search_and_availability(
        self, mocked_has_permission, mocked_module_active
    ):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("library:books"),
            {"q": "physics", "availability": "available"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Physics Fundamentals")
        self.assertNotContains(response, "History Atlas")
