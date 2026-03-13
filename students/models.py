from django.db import models
from django.utils.translation import gettext_lazy as _


class StudentPromotionHistory(models.Model):
    """Track student promotion history."""

    student = models.ForeignKey(
        "Student", on_delete=models.CASCADE, related_name="promotions"
    )
    from_class = models.ForeignKey(
        "ClassLevel", on_delete=models.CASCADE, related_name="promoted_from"
    )
    to_class = models.ForeignKey(
        "ClassLevel", on_delete=models.CASCADE, related_name="promoted_to"
    )
    from_academic_year = models.ForeignKey(
        "AcademicYear", on_delete=models.CASCADE, related_name="promotions_from"
    )
    to_academic_year = models.ForeignKey(
        "AcademicYear", on_delete=models.CASCADE, related_name="promotions_to"
    )
    promoted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="student_promotions",
    )
    promoted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "students_promotion_history"
        verbose_name = _("student promotion history")
        verbose_name_plural = _("student promotion histories")
        ordering = ["-promoted_at"]

    def __str__(self):
        return (
            f"{self.student} promoted from {self.from_class} to {self.to_class}"
        )


class AcademicYear(models.Model):
    """Academic year model."""

    name = models.CharField(max_length=20, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "students_academic_year"
        verbose_name = _("academic year")
        verbose_name_plural = _("academic years")
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(
                is_current=False
            )
        super().save(*args, **kwargs)


class Department(models.Model):
    """Department model."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "students_department"
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    """Class/Grade level model."""

    name = models.CharField(max_length=50, unique=True)
    numeric_name = models.IntegerField(unique=True)
    stream = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("science", "Science"),
            ("commerce", "Commerce"),
            ("arts", "Arts"),
            ("", "None"),
        ],
    )
    capacity = models.IntegerField(default=40)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "students_class_level"
        verbose_name = _("class level")
        verbose_name_plural = _("class levels")
        ordering = ["numeric_name"]

    def __str__(self):
        return self.name


class Section(models.Model):
    """Section model."""

    name = models.CharField(max_length=10)
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.CASCADE, related_name="sections"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="sections"
    )
    capacity = models.IntegerField(default=40)
    room_no = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "students_section"
        verbose_name = _("section")
        verbose_name_plural = _("sections")
        unique_together = ["class_level", "name", "academic_year"]
        ordering = ["name"]

    def __str__(self):
        return f"{self.class_level.name} - {self.name}"


class Student(models.Model):
    """Student model."""

    RELIGION_CHOICES = [
        ("islam", "Islam"),
        ("hinduism", "Hinduism"),
        ("christianity", "Christianity"),
        ("buddhism", "Buddhism"),
        ("other", "Other"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("O+", "O+"),
        ("O-", "O-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
    ]

    # User association
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    # Admission details
    admission_no = models.CharField(max_length=50, unique=True)
    admission_date = models.DateField()
    roll_number = models.IntegerField(null=True, blank=True)

    # Personal details
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_group = models.CharField(
        max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True
    )
    religion = models.CharField(
        max_length=20, choices=RELIGION_CHOICES, blank=True
    )
    aadhar_no = models.CharField(max_length=20, blank=True)

    # Academic details
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.CASCADE, related_name="students"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="students",
        null=True,
        blank=True,
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="students"
    )
    house = models.CharField(max_length=50, blank=True)

    # Previous school
    previous_school = models.CharField(max_length=200, blank=True)
    tc_no = models.CharField(max_length=50, blank=True)
    tc_date = models.DateField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        default="studying",
        choices=[
            ("studying", "Studying"),
            ("transferred", "Transferred"),
            ("passed_out", "Passed Out"),
            ("left", "Left"),
            ("suspended", "Suspended"),
        ],
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "students_student"
        verbose_name = _("student")
        verbose_name_plural = _("students")
        ordering = ["roll_number", "admission_no"]

    def __str__(self):
        return f"{self.admission_no} - {self.user.get_full_name()}"

    def get_full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def attendance_percentage(self):
        """Calculate attendance percentage."""
        from attendance.models import Attendance

        total_days = Attendance.objects.filter(
            student=self, academic_year=self.academic_year
        ).count()
        if total_days == 0:
            return 0
        present_days = Attendance.objects.filter(
            student=self, academic_year=self.academic_year, status="present"
        ).count()
        return round((present_days / total_days) * 100, 2)
