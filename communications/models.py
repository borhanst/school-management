from django.db import models
from django.utils.translation import gettext_lazy as _


class Message(models.Model):
    """Message model for communication between users."""

    sender = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    parent_thread = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "communications_message"
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} -> {self.receiver} - {self.subject}"


class Notice(models.Model):
    """Notice model for announcements."""

    NOTICE_TYPE_CHOICES = [
        ("general", "General"),
        ("academic", "Academic"),
        ("event", "Event"),
        ("fee", "Fee"),
        ("exam", "Exam"),
        ("holiday", "Holiday"),
        ("urgent", "Urgent"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    notice_type = models.CharField(
        max_length=20, choices=NOTICE_TYPE_CHOICES, default="general"
    )
    posted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_notices",
    )
    for_roles = models.JSONField(
        default=list, help_text="List of roles to show notice to"
    )
    for_classes = models.ManyToManyField(
        "students.ClassLevel", blank=True, related_name="notices"
    )
    attachment = models.FileField(
        upload_to="notices/attachments/", blank=True, null=True
    )
    publish_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "communications_notice"
        verbose_name = _("notice")
        verbose_name_plural = _("notices")
        ordering = ["-is_pinned", "-publish_date"]

    def __str__(self):
        return self.title


class NoticeView(models.Model):
    """Track who has viewed a notice."""

    notice = models.ForeignKey(
        Notice, on_delete=models.CASCADE, related_name="views"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notice_views"
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "communications_notice_view"
        verbose_name = _("notice view")
        verbose_name_plural = _("notice views")
        unique_together = ["notice", "user"]

    def __str__(self):
        return f"{self.notice} - {self.user}"


class Announcement(models.Model):
    """Announcement model for quick broadcasts."""

    title = models.CharField(max_length=200)
    message = models.TextField()
    announcement_type = models.CharField(max_length=20, default="info")
    sent_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    recipients = models.JSONField(default=list)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "communications_announcement"
        verbose_name = _("announcement")
        verbose_name_plural = _("announcements")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
