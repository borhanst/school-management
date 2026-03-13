from django.db import models
from django.utils.translation import gettext_lazy as _

# Dashboard models can be empty for now since we'll use aggregated data from other models
# Any custom dashboard widgets or analytics can be added here


class DashboardWidget(models.Model):
    """Custom dashboard widget model."""

    WIDGET_TYPES = [
        ("stats", "Statistics"),
        ("chart", "Chart"),
        ("table", "Table"),
        ("list", "List"),
    ]

    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    config = models.JSONField(default=dict, help_text="Widget configuration")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    for_roles = models.JSONField(default=list)

    class Meta:
        db_table = "dashboard_widget"
        verbose_name = _("dashboard widget")
        verbose_name_plural = _("dashboard widgets")
        ordering = ["order"]

    def __str__(self):
        return self.name


class SystemSettings(models.Model):
    """System settings model."""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default="general")
    is_public = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_settings"
        verbose_name = _("system setting")
        verbose_name_plural = _("system settings")

    def __str__(self):
        return self.key
