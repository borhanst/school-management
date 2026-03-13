from django.db import models
from django.utils.translation import gettext_lazy as _


class Subject(models.Model):
    """Subject model."""

    SUBJECT_TYPE_CHOICES = [
        ("core", "Core"),
        ("elective", "Elective"),
        ("practical", "Practical"),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    subject_type = models.CharField(
        max_length=20, choices=SUBJECT_TYPE_CHOICES, default="core"
    )
    class_level = models.ForeignKey(
        "students.ClassLevel", on_delete=models.CASCADE, related_name="subjects"
    )
    teacher = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subjects",
    )
    credit_hours = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "academics_subject"
        verbose_name = _("subject")
        verbose_name_plural = _("subjects")
        unique_together = ["code", "class_level"]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Period(models.Model):
    """Period/Timing model."""

    period_no = models.IntegerField(unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)
    break_duration = models.IntegerField(
        default=0, help_text="Break duration in minutes"
    )

    class Meta:
        db_table = "academics_period"
        verbose_name = _("period")
        verbose_name_plural = _("periods")
        ordering = ["period_no"]

    def __str__(self):
        return f"Period {self.period_no}"


class Timetable(models.Model):
    """Timetable model."""

    DAYS_OF_WEEK = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    section = models.ForeignKey(
        "students.Section", on_delete=models.CASCADE, related_name="timetables"
    )
    period = models.ForeignKey(
        Period, on_delete=models.CASCADE, related_name="timetables"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="timetables"
    )
    teacher = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timetables",
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    room_no = models.CharField(max_length=20, blank=True)
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="timetables",
    )

    class Meta:
        db_table = "academics_timetable"
        verbose_name = _("timetable")
        verbose_name_plural = _("timetables")
        unique_together = ["section", "period", "day_of_week", "academic_year"]
        ordering = ["day_of_week", "period__period_no"]

    def __str__(self):
        return f"{self.section} - {self.subject} - {self.get_day_of_week_display()}"


class TeacherSubjectAssignment(models.Model):
    """Teacher subject assignment model."""

    teacher = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.CASCADE,
        related_name="subject_assignments",
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="teacher_assignments"
    )
    section = models.ForeignKey(
        "students.Section",
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    is_class_teacher = models.BooleanField(default=False)

    class Meta:
        db_table = "academics_teacher_subject_assignment"
        verbose_name = _("teacher subject assignment")
        verbose_name_plural = _("teacher subject assignments")
        unique_together = ["subject", "section", "academic_year"]

    def __str__(self):
        return f"{self.teacher} - {self.subject} - {self.section}"
