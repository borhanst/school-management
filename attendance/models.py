from django.db import models
from django.utils.translation import gettext_lazy as _


class Attendance(models.Model):
    """Daily attendance model."""

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("leave", "On Leave"),
    ]

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="attendances"
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="present"
    )
    period = models.ForeignKey(
        "academics.Period",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendances",
    )
    marked_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_attendances",
    )
    remarks = models.TextField(blank=True)
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="attendances",
    )

    class Meta:
        db_table = "attendance_attendance"
        verbose_name = _("attendance")
        verbose_name_plural = _("attendances")
        unique_together = ["student", "date", "period"]
        ordering = ["-date", "student__roll_number"]

    def __str__(self):
        return f"{self.student} - {self.date} - {self.get_status_display()}"


class AttendanceSession(models.Model):
    """Attendance session for marking attendance."""

    section = models.ForeignKey(
        "students.Section",
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
    )
    date = models.DateField()
    period = models.ForeignKey(
        "academics.Period", on_delete=models.SET_NULL, null=True, blank=True
    )
    marked_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_locked = models.BooleanField(default=False)
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attendance_session"
        verbose_name = _("attendance session")
        verbose_name_plural = _("attendance sessions")
        unique_together = ["section", "date", "period"]

    def __str__(self):
        return f"{self.section} - {self.date}"


class TeacherAttendancePermission(models.Model):
    """Model to store which teachers can mark attendance for which sections."""

    teacher = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.CASCADE,
        related_name="attendance_permissions",
    )
    section = models.ForeignKey(
        "students.Section",
        on_delete=models.CASCADE,
        related_name="attendance_permissions",
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="teacher_attendance_permissions",
    )
    granted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="granted_attendance_permissions",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attendance_teacher_permission"
        verbose_name = _("teacher attendance permission")
        verbose_name_plural = _("teacher attendance permissions")
        unique_together = ["teacher", "section", "academic_year"]

    def __str__(self):
        return f"{self.teacher} - {self.section} - {self.academic_year}"


class LeaveRequest(models.Model):
    """Leave request model."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending"
    )
    approved_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    remarks = models.TextField(blank=True)
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "attendance_leave_request"
        verbose_name = _("leave request")
        verbose_name_plural = _("leave requests")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} - {self.from_date} to {self.to_date}"
