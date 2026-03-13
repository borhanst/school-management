from django.apps import AppConfig


class RolesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "roles"
    verbose_name = "Role Management"

    def ready(self):
        import roles.signals  # noqa: F401
