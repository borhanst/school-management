from django.db import models
from django.utils.translation import gettext_lazy as _


class Term(models.Model):
    """Academic term model."""

    name = models.CharField(max_length=50)
    academic_year = models.ForeignKey(
        "students.AcademicYear", on_delete=models.CASCADE, related_name="terms"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "examinations_term"
        verbose_name = _("term")
        verbose_name_plural = _("terms")
        unique_together = ["name", "academic_year"]
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.name} - {self.academic_year}"


class ExamType(models.Model):
    """Exam type model."""

    name = models.CharField(max_length=50)
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="exam_types",
    )
    weightage = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Weightage in percentage"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "examinations_exam_type"
        verbose_name = _("exam type")
        verbose_name_plural = _("exam types")
        unique_together = ["name", "academic_year"]

    def __str__(self):
        return f"{self.name} ({self.weightage}%)"


class ExamSchedule(models.Model):
    """Exam schedule model."""

    exam_type = models.ForeignKey(
        ExamType, on_delete=models.CASCADE, related_name="schedules"
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="exam_schedules",
    )
    class_level = models.ForeignKey(
        "students.ClassLevel",
        on_delete=models.CASCADE,
        related_name="exam_schedules",
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="exam_schedules",
        null=True
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    marks = models.IntegerField()
    room_no = models.CharField(max_length=20, blank=True)
    instructions = models.TextField(blank=True)
    question_paper = models.ForeignKey(
        "questions.QuestionPaper",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exam_schedules",
        help_text=_("Question paper to be used for this exam"),
    )
    is_published = models.BooleanField(
        default=False,
        help_text=_("Whether this exam schedule is published and visible to students"),
    )

    class Meta:
        db_table = "examinations_schedule"
        verbose_name = _("exam schedule")
        verbose_name_plural = _("exam schedules")
        unique_together = [
            "exam_type",
            "subject",
            "class_level",
            "academic_year",
        ]
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.exam_type} - {self.subject} - {self.class_level}"


class Grade(models.Model):
    """Grade/Result model."""

    GRADE_CHOICES = [
        ("A+", "A+"),
        ("A", "A"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B", "B"),
        ("B-", "B-"),
        ("C+", "C+"),
        ("C", "C"),
        ("C-", "C-"),
        ("D", "D"),
        ("F", "Fail"),
    ]

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="grades"
    )
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.CASCADE, related_name="grades"
    )
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.CASCADE, related_name="grades"
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="grades",
        null=True,
        blank=True,
    )
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    grade_letter = models.CharField(max_length=2, choices=GRADE_CHOICES)
    remarks = models.TextField(blank=True)
    entered_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_grades",
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear", on_delete=models.CASCADE, related_name="grades"
    )

    class Meta:
        db_table = "examinations_grade"
        verbose_name = _("grade")
        verbose_name_plural = _("grades")
        unique_together = ["student", "subject", "exam_type", "academic_year"]
        ordering = ["student", "subject", "exam_type"]

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.marks} ({self.grade_letter})"


class GradeDistribution(models.Model):
    """Grade distribution for subjects."""

    class_level = models.ForeignKey(
        "students.ClassLevel",
        on_delete=models.CASCADE,
        related_name="grade_distributions",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="grade_distributions",
    )
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.CASCADE, related_name="grade_distributions"
    )
    min_marks = models.DecimalField(max_digits=5, decimal_places=2)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2)
    grade_letter = models.CharField(max_length=2)
    grade_points = models.DecimalField(
        max_digits=3, decimal_places=2, default=0
    )

    class Meta:
        db_table = "examinations_grade_distribution"
        verbose_name = _("grade distribution")
        verbose_name_plural = _("grade distributions")
        unique_together = [
            "class_level",
            "subject",
            "exam_type",
            "grade_letter",
        ]

    def __str__(self):
        return f"{self.class_level} - {self.subject} - {self.grade_letter}"
