from django.db import models
from django.utils.translation import gettext_lazy as _


class BookCategory(models.Model):
    """Book category model."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "library_category"
        verbose_name = _("book category")
        verbose_name_plural = _("book categories")

    def __str__(self):
        return self.name


class Book(models.Model):
    """Book model."""

    isbn = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    publisher = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(
        BookCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
    )
    rack_no = models.CharField(max_length=20, blank=True)
    shelf_no = models.CharField(max_length=20, blank=True)
    quantity = models.IntegerField(default=1)
    available = models.IntegerField(default=1)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cover_image = models.ImageField(
        upload_to="library/covers/", blank=True, null=True
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "library_book"
        verbose_name = _("book")
        verbose_name_plural = _("books")
        ordering = ["title"]

    def __str__(self):
        return self.title


class BookIssue(models.Model):
    """Book issue/return model."""

    STATUS_CHOICES = [
        ("issued", "Issued"),
        ("returned", "Returned"),
        ("overdue", "Overdue"),
    ]

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="book_issues"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="issues"
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="issued"
    )
    issued_by = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_books",
    )
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "library_book_issue"
        verbose_name = _("book issue")
        verbose_name_plural = _("book issues")
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.student} - {self.book} - {self.status}"


class LibraryMember(models.Model):
    """Library member model."""

    student = models.OneToOneField(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="library_member",
    )
    member_since = models.DateField(auto_now_add=True)
    membership_type = models.CharField(max_length=50, default="student")
    is_active = models.BooleanField(default=True)
    max_books = models.IntegerField(default=3)

    class Meta:
        db_table = "library_member"
        verbose_name = _("library member")
        verbose_name_plural = _("library members")

    def __str__(self):
        return f"{self.student} - {self.member_since}"

    @property
    def issued_books_count(self):
        return self.book_issues.filter(status="issued").count()
