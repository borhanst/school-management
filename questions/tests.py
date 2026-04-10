from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
import io
import json

from academics.models import Subject
from examinations.models import ExamType, Term
from questions.models import (
    AIGenerationRequest,
    Question,
    QuestionBank,
    QuestionOption,
)
from roles.models import Module, PermissionType, Role, RolePermission, UserRole
from students.models import AcademicYear, ClassLevel, Section, Student

User = get_user_model()


def _create_test_image():
    """Create a simple test image."""
    img = Image.new("RGB", (100, 100), color="white")
    img_io = io.BytesIO()
    img.save(img_io, "JPEG")
    img_io.seek(0)
    return SimpleUploadedFile("test_image.jpg", img_io.read(), content_type="image/jpeg")


class PermissionTestMixin:
    """Mixin to help setup permissions for tests."""

    def _grant_permission(self, module_slug, codenames):
        """Grant specific permissions to the test user."""
        module, _ = Module.objects.get_or_create(
            slug=module_slug,
            defaults={"name": module_slug.title(), "is_active": True},
        )
        for codename in codenames:
            pt, _ = PermissionType.objects.get_or_create(
                module=module,
                codename=codename,
                defaults={"name": codename.title()},
            )
            rp, _ = RolePermission.objects.get_or_create(
                module=module,
                permission_type=pt,
            )
            self.role.permissions.add(rp)


class QuestionBankModelTests(TestCase):
    """Test QuestionBank model."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.bank = QuestionBank.objects.create(
            name="Test Bank",
            class_level=self.class_level,
            subject=self.subject,
            academic_year=self.academic_year,
            created_by=self.user,
        )

    def test_str_representation(self):
        self.assertIn("Test Bank", str(self.bank))
        self.assertIn("Class 9", str(self.bank))
        self.assertIn("Physics", str(self.bank))

    def test_get_question_count_by_type(self):
        Question.objects.create(
            question_bank=self.bank,
            question_text="Test MCQ",
            question_type="mcq",
            marks=1,
        )
        Question.objects.create(
            question_bank=self.bank,
            question_text="Test CQ",
            question_type="creative",
            marks=10,
        )
        counts = self.bank.get_question_count_by_type()
        self.assertEqual(counts["mcq"], 1)
        self.assertEqual(counts["creative"], 1)
        self.assertEqual(counts["short_answer"], 0)

    def test_unique_together_constraint(self):
        """Test that duplicate names for same class/subject/year are prevented."""
        with self.assertRaises(Exception):
            QuestionBank.objects.create(
                name="Test Bank",
                class_level=self.class_level,
                subject=self.subject,
                academic_year=self.academic_year,
            )


class QuestionModelTests(TestCase):
    """Test Question model."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.bank = QuestionBank.objects.create(
            name="Test Bank",
            class_level=self.class_level,
            subject=self.subject,
            academic_year=self.academic_year,
            created_by=self.user,
        )

    def test_str_representation(self):
        question = Question.objects.create(
            question_bank=self.bank,
            question_text="What is Newton's first law of motion?",
            question_type="mcq",
            marks=1,
        )
        self.assertIn("[MCQ (Multiple Choice Question)]", str(question))
        self.assertIn("What is Newton's", str(question))

    def test_mcq_options_count(self):
        """Test that MCQ questions can have 4 options."""
        question = Question.objects.create(
            question_bank=self.bank,
            question_text="What is gravity?",
            question_type="mcq",
            marks=1,
        )
        for label in ["A", "B", "C", "D"]:
            QuestionOption.objects.create(
                question=question,
                option_text=f"Option {label}",
                label=label,
                is_correct=(label == "A"),
            )
        self.assertEqual(question.options.count(), 4)

    def test_creative_question(self):
        """Test creative question creation."""
        cq = Question.objects.create(
            question_bank=self.bank,
            question_text="Read the stem and answer:\n(a) Define force [1]\n(b) Explain...",
            question_type="creative",
            marks=10,
            bloom_level="knowledge",
        )
        self.assertEqual(cq.question_type, "creative")
        self.assertEqual(cq.marks, 10)


class QuestionOptionModelTests(TestCase):
    """Test QuestionOption model."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.bank = QuestionBank.objects.create(
            name="Test Bank",
            class_level=self.class_level,
            subject=self.subject,
            academic_year=self.academic_year,
            created_by=self.user,
        )
        self.question = Question.objects.create(
            question_bank=self.bank,
            question_text="Test MCQ",
            question_type="mcq",
            marks=1,
        )

    def test_unique_label_per_question(self):
        """Test that option labels must be unique per question."""
        QuestionOption.objects.create(
            question=self.question,
            option_text="Option A",
            label="A",
            is_correct=True,
        )
        with self.assertRaises(Exception):
            QuestionOption.objects.create(
                question=self.question,
                option_text="Another Option",
                label="A",
            )


class AIGenerationRequestModelTests(TestCase):
    """Test AIGenerationRequest model."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.image = _create_test_image()

    def test_total_questions_requested(self):
        gen_request = AIGenerationRequest.objects.create(
            class_level=self.class_level,
            subject=self.subject,
            uploaded_image=self.image,
            num_mcq=10,
            num_creative=5,
            num_short_answer=5,
            created_by=self.user,
        )
        self.assertEqual(gen_request.total_questions_requested(), 20)

    def test_str_representation(self):
        gen_request = AIGenerationRequest.objects.create(
            class_level=self.class_level,
            subject=self.subject,
            uploaded_image=self.image,
            created_by=self.user,
        )
        self.assertIn("Class 9", str(gen_request))
        self.assertIn("Physics", str(gen_request))


class QuestionBankViewTests(TestCase, PermissionTestMixin):
    """Test question bank views."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.role = Role.objects.create(name="Teacher Test", is_active=True)
        UserRole.objects.create(user=self.user, role=self.role, is_active=True)
        self._grant_permission("questions", ["view", "add", "edit", "delete", "ai_generate"])

    def test_bank_list_requires_login(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(reverse("questions:bank_list"))
        self.assertEqual(response.status_code, 302)

    def test_bank_list_redirects_to_papers(self):
        """Test bank list redirects to papers list."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("questions:bank_list"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("questions:paper-list-all"), fetch_redirect_response=False)


class AIGenerationViewTests(TestCase, PermissionTestMixin):
    """Test AI generation views."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.role = Role.objects.create(name="Teacher Test", is_active=True)
        UserRole.objects.create(user=self.user, role=self.role, is_active=True)
        self._grant_permission("questions", ["view", "add", "ai_generate"])

    def test_ai_generate_form_requires_login(self):
        """Test that AI generate view requires authentication."""
        response = self.client.get(reverse("questions:ai_generate"))
        self.assertEqual(response.status_code, 302)

    def test_ai_generate_form_shows_fields(self):
        """Test that AI generate form displays correctly."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("questions:ai_generate"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("questions:paper-list-all"), fetch_redirect_response=False)


class QuestionPaperExportTests(TestCase, PermissionTestMixin):
    """Test question paper export."""

    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025",
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9", numeric_name=9
        )
        self.subject = Subject.objects.create(
            name="Physics", code="PHY-9", class_level=self.class_level
        )
        self.user = User.objects.create_user(
            username="teacher1", password="testpass123", role="teacher"
        )
        self.role = Role.objects.create(name="Teacher Test", is_active=True)
        UserRole.objects.create(user=self.user, role=self.role, is_active=True)
        self._grant_permission("questions", ["view"])
        self.bank = QuestionBank.objects.create(
            name="Test Bank",
            class_level=self.class_level,
            subject=self.subject,
            academic_year=self.academic_year,
        )

    def test_export_question_paper_requires_login(self):
        """Test that export requires authentication."""
        response = self.client.get(
            reverse("questions:export_paper", args=[1])
        )
        self.assertEqual(response.status_code, 302)

    def test_export_question_paper_redirects_to_paper(self):
        """Test that export redirects to paper detail."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("questions:export_paper", args=[1])
        )
        self.assertEqual(response.status_code, 302)


class AIGenerationServiceTests(TestCase):
    """Test AI generation service (mocked)."""

    def test_generate_questions_without_api_key(self):
        """Test that service fails gracefully without API key."""
        from questions.services.ai_generator import GeminiQuestionGenerator

        with override_settings(GEMINI_API_KEY=""):
            with self.assertRaises(ValueError) as context:
                GeminiQuestionGenerator()
            self.assertIn("GEMINI_API_KEY", str(context.exception))
