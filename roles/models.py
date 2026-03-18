from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


class Module(models.Model):
    """Dynamic module definition - allows creating modules through admin."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Font Awesome icon class"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Module"
        verbose_name_plural = "Modules"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_permissions(self):
        """Get all permissions for this module."""
        return self.permission_types.all()


class PermissionType(models.Model):
    """Defines available actions/permission types for a module."""

    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="permission_types"
    )
    name = models.CharField(
        max_length=50, help_text="Display name (e.g., 'View', 'Create')"
    )
    codename = models.SlugField(
        max_length=50, help_text="Code name (e.g., 'view', 'create')"
    )
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ["module", "codename"]
        verbose_name = "Permission Type"
        verbose_name_plural = "Permission Types"

    def __str__(self):
        return f"{self.module.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.codename:
            self.codename = slugify(self.name)
        super().save(*args, **kwargs)


class Role(models.Model):
    """Role with permissions from multiple modules."""

    DEFAULT_ROLE_TYPE_CHOICES = [
        ("", "No default user type"),
        ("admin", "Administrator"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False, help_text="Default role for new users"
    )
    default_for_role = models.CharField(
        max_length=20,
        choices=DEFAULT_ROLE_TYPE_CHOICES,
        blank=True,
        default="",
        help_text="Automatically assign this role to new users of the selected type.",
    )
    priority = models.PositiveIntegerField(
        default=0, help_text="Higher priority roles take precedence"
    )
    permissions = models.ManyToManyField(
        "RolePermission",
        blank=True,
        related_name="roles",
        help_text="Select permissions for this role",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["-priority", "name"]

    def __str__(self):
        return self.name

    def get_permissions_list(self):
        """Get list of permission strings."""
        perms = []
        for rp in self.permissions.all():
            perms.append(f"{rp.module.slug}_{rp.permission_type.codename}")
        return perms

    def has_permission(self, module_slug, action):
        """Check if role has specific permission."""
        return self.permissions.filter(
            module__slug=module_slug, permission_type__codename=action
        ).exists()


class RolePermission(models.Model):
    """Link between Role and Module Permissions."""

    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    permission_type = models.ForeignKey(
        PermissionType, on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["module", "permission_type"]
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"

    def __str__(self):
        return f"{self.module.name} - {self.permission_type.name}"

    @property
    def codename(self):
        return f"{self.module.slug}_{self.permission_type.codename}"


class UserRole(models.Model):
    """Assignment of roles to users - supports multiple roles per user."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="user_assignments"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_user_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="Optional expiration date"
    )
    is_active = models.BooleanField(
        default=True, help_text="Toggle role on/off without deleting"
    )

    class Meta:
        unique_together = ["user", "role"]
        verbose_name = "User Role Assignment"
        verbose_name_plural = "User Role Assignments"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    def is_expired(self):
        """Check if role assignment has expired."""
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False

    def is_active_and_valid(self):
        """Check if role assignment is active and not expired."""
        return self.is_active and not self.is_expired()


class UserPermission(models.Model):
    """Direct permission assignment to a user without a role."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="direct_permission_assignments",
    )
    role_permission = models.ForeignKey(
        RolePermission,
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_user_permissions",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="Optional expiration date"
    )
    is_active = models.BooleanField(
        default=True, help_text="Toggle permission on/off without deleting"
    )

    class Meta:
        unique_together = ["user", "role_permission"]
        verbose_name = "User Permission Assignment"
        verbose_name_plural = "User Permission Assignments"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.user.username} - {self.role_permission.codename}"

    @property
    def module(self):
        return self.role_permission.module

    @property
    def permission_type(self):
        return self.role_permission.permission_type

    @property
    def codename(self):
        return self.role_permission.codename

    def is_expired(self):
        """Check if direct permission assignment has expired."""
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False

    def is_active_and_valid(self):
        """Check if direct permission assignment is active and not expired."""
        return self.is_active and not self.is_expired()
