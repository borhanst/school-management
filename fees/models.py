from django.db import models
from django.utils.translation import gettext_lazy as _


class FeeType(models.Model):
    """Fee type model."""

    CATEGORY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annual", "Annual"),
        ("one_time", "One Time"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="monthly"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "fees_fee_type"
        verbose_name = _("fee type")
        verbose_name_plural = _("fee types")

    def __str__(self):
        return self.name


class FeeStructure(models.Model):
    """Fee structure model."""

    class_level = models.ForeignKey(
        "students.ClassLevel",
        on_delete=models.CASCADE,
        related_name="fee_structures",
    )
    fee_type = models.ForeignKey(
        FeeType, on_delete=models.CASCADE, related_name="fee_structures"
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="fee_structures",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    late_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Late fee per day"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "fees_fee_structure"
        verbose_name = _("fee structure")
        verbose_name_plural = _("fee_structures")
        unique_together = ["class_level", "fee_type", "academic_year"]

    def __str__(self):
        return f"{self.class_level} - {self.fee_type} - {self.amount}"


class FeeInvoice(models.Model):
    """Fee invoice model."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("partial", "Partial"),
        ("overdue", "Overdue"),
        ("waived", "Waived"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="fee_invoices",
    )
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name="invoices"
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="fee_invoices",
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fees_invoice"
        verbose_name = _("fee invoice")
        verbose_name_plural = _("fee invoices")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} - {self.fee_structure} - {self.status}"

    def save(self, *args, **kwargs):
        self.due_amount = self.total_amount - self.paid_amount
        if self.due_amount <= 0:
            self.status = "paid"
        elif self.paid_amount > 0:
            self.status = "partial"
        super().save(*args, **kwargs)


class FeePayment(models.Model):
    """Fee payment model."""

    PAYMENT_MODE_CHOICES = [
        ("cash", "Cash"),
        ("cheque", "Cheque"),
        ("online", "Online"),
        ("bank_transfer", "Bank Transfer"),
        ("card", "Card"),
    ]

    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_mode = models.CharField(
        max_length=20, choices=PAYMENT_MODE_CHOICES, default="cash"
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    receipt_no = models.CharField(max_length=50, unique=True)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remarks = models.TextField(blank=True)
    received_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fee_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fees_payment"
        verbose_name = _("fee payment")
        verbose_name_plural = _("fee payments")
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.invoice} - {self.amount} - {self.receipt_no}"


class FeeWaiver(models.Model):
    """Fee waiver model."""

    REASON_CHOICES = [
        ("scholarship", "Scholarship"),
        ("financial_aid", "Financial Aid"),
        ("staff_ward", "Staff Ward"),
        ("other", "Other"),
    ]

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="fee_waivers"
    )
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name="waivers"
    )
    waiver_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    approved_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fees_waiver"
        verbose_name = _("fee waiver")
        verbose_name_plural = _("fee waivers")

    def __str__(self):
        return f"{self.student} - {self.fee_structure} - {self.waiver_amount}"
