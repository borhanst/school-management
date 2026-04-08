from django.db import models
from django.utils.translation import gettext_lazy as _


class QuestionBank(models.Model):
    """Container for organizing questions by class, subject, and topic."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    class_level = models.ForeignKey(
        "students.ClassLevel",
        on_delete=models.CASCADE,
        related_name="question_banks",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="question_banks",
    )
    term = models.ForeignKey(
        "examinations.Term",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_banks",
    )
    topic = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Specific topic/chapter name"),
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="question_banks",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_question_banks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "questions_question_bank"
        verbose_name = _("question bank")
        verbose_name_plural = _("question banks")
        ordering = ["-created_at"]
        unique_together = ["name", "class_level", "subject", "academic_year"]

    def __str__(self):
        return f"{self.name} - {self.class_level} {self.subject}"

    def get_question_count_by_type(self):
        """Return count of questions by type."""
        return {
            "mcq": self.questions.filter(question_type="mcq").count(),
            "creative": self.questions.filter(question_type="creative").count(),
            "short_answer": self.questions.filter(
                question_type="short_answer"
            ).count(),
        }


class Question(models.Model):
    """Individual question with support for bilingual content."""

    QUESTION_TYPE_CHOICES = [
        ("mcq", _("MCQ (Multiple Choice Question)")),
        ("creative", _("Creative Question (CQ)")),
        ("short_answer", _("Short Answer")),
    ]

    DIFFICULTY_CHOICES = [
        ("easy", _("Easy")),
        ("medium", _("Medium")),
        ("hard", _("Hard")),
    ]

    BLOOM_LEVEL_CHOICES = [
        ("knowledge", _("Knowledge")),
        ("comprehension", _("Comprehension")),
        ("application", _("Application")),
        ("analysis", _("Analysis")),
        ("synthesis", _("Synthesis")),
        ("evaluation", _("Evaluation")),
    ]

    question_bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField(help_text=_("Question in English"))
    question_text_bn = models.TextField(
        blank=True, help_text=_("Question in Bengali")
    )
    question_type = models.CharField(
        max_length=20, choices=QUESTION_TYPE_CHOICES, default="mcq"
    )
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default="medium"
    )
    bloom_level = models.CharField(
        max_length=20,
        choices=BLOOM_LEVEL_CHOICES,
        default="knowledge",
        help_text=_("Bloom's taxonomy level (for creative questions)"),
    )
    marks = models.IntegerField(
        default=1, help_text=_("Marks allocated for this question")
    )
    answer_explanation = models.TextField(
        blank=True, help_text=_("Correct answer explanation")
    )
    answer_explanation_bn = models.TextField(
        blank=True, help_text=_("Correct answer explanation in Bengali")
    )
    ai_generated = models.BooleanField(
        default=False, help_text=_("Whether this question was AI-generated")
    )
    generation_request = models.ForeignKey(
        "AIGenerationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_questions",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(
        default=False, help_text=_("Whether question has been reviewed")
    )

    class Meta:
        db_table = "questions_question"
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        ordering = ["question_bank", "question_type", "-created_at"]
        indexes = [
            models.Index(fields=["question_type", "difficulty"]),
            models.Index(fields=["question_bank", "is_approved"]),
        ]

    def __str__(self):
        type_display = self.get_question_type_display()
        return f"[{type_display}] {self.question_text[:50]}..."


class QuestionOption(models.Model):
    """Options for MCQ questions."""

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
        limit_choices_to={"question_type": "mcq"},
    )
    option_text = models.CharField(max_length=500, help_text=_("Option text"))
    option_text_bn = models.CharField(
        max_length=500, blank=True, help_text=_("Option text in Bengali")
    )
    label = models.CharField(
        max_length=1,
        help_text=_("Option label (A, B, C, D)"),
    )
    is_correct = models.BooleanField(
        default=False, help_text=_("Whether this is the correct answer")
    )

    class Meta:
        db_table = "questions_question_option"
        verbose_name = _("question option")
        verbose_name_plural = _("question options")
        ordering = ["question", "label"]
        unique_together = ["question", "label"]

    def __str__(self):
        return f"{self.label}. {self.option_text[:30]}..."


class AIGenerationRequest(models.Model):
    """Tracks AI generation requests with uploaded images."""

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("processing", _("Processing")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
    ]

    class_level = models.ForeignKey(
        "students.ClassLevel",
        on_delete=models.CASCADE,
        related_name="ai_generation_requests",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="ai_generation_requests",
    )
    term = models.ForeignKey(
        "examinations.Term",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_generation_requests",
    )
    uploaded_image = models.ImageField(
        upload_to="questions/ai_uploads/",
        help_text=_("Uploaded textbook page image"),
    )
    num_mcq = models.IntegerField(
        default=10, help_text=_("Number of MCQs to generate")
    )
    num_creative = models.IntegerField(
        default=5, help_text=_("Number of creative questions to generate")
    )
    num_short_answer = models.IntegerField(
        default=5, help_text=_("Number of short answer questions to generate")
    )
    additional_prompt = models.TextField(
        blank=True,
        help_text=_(
            "Additional instructions for AI (topics, focus areas, etc.)"
        ),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    prompt_used = models.TextField(
        blank=True, help_text=_("The full prompt sent to AI")
    )
    ai_response_raw = models.JSONField(
        blank=True, null=True, help_text=_("Raw JSON response from AI")
    )
    error_message = models.TextField(
        blank=True, help_text=_("Error message if generation failed")
    )
    language = models.CharField(
        max_length=20,
        default="bilingual",
        help_text=_("Generation language: english, bengali, bilingual"),
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_generation_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "questions_ai_generation_request"
        verbose_name = _("AI generation request")
        verbose_name_plural = _("AI generation requests")
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"AI Generation: {self.class_level} {self.subject} "
            f"({self.get_status_display()})"
        )

    def total_questions_requested(self):
        """Return total number of questions requested."""
        return self.num_mcq + self.num_creative + self.num_short_answer
