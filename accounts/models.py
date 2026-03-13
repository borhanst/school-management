from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from roles.permissions import (
    SUPERUSER_PERMISSION,
    build_permission_key,
    has_permission_key,
)


class User(AbstractUser):
    """Custom User model with role-based access control."""

    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent"),
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

    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="student"
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(
        max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True
    )
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "accounts_user"
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.get_full_name() or self.username

    # ==================== Permission Methods (Enhanced with Caching) ====================

    def get_all_permissions(self, force_refresh=False):
        """
        Get all aggregated permissions from all active roles.
        Uses Django cache for performance.

        Args:
            force_refresh: If True, bypass cache and rebuild permissions

        Returns:
            set: Permission strings like {'students_view', 'fees_add'}
        """
        if not self.is_active:
            return set()

        # Superusers have all permissions
        if self.is_superuser:
            return {SUPERUSER_PERMISSION}

        # Check cache first (unless force_refresh)
        if not force_refresh:
            cache_key = f"user_perms_{self.id}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        permissions = set()

        # Aggregate permissions from all active role assignments
        active_assignments = (
            self.user_roles.filter(is_active=True, role__is_active=True)
            .select_related("role")
            .prefetch_related(
                "role__permissions__module",
                "role__permissions__permission_type",
            )
        )

        for user_role in active_assignments:
            if user_role.is_expired():
                continue
            for role_perm in user_role.role.permissions.all():
                perm_string = build_permission_key(
                    role_perm.module.slug, role_perm.permission_type.codename
                )
                permissions.add(perm_string)

        # Check for denied permissions (explicit denies override grants)
        denied = self._get_denied_permissions()
        if denied:
            # Remove any denied permissions
            permissions -= denied

        # Cache for 5 minutes (300 seconds)
        cache_key = f"user_perms_{self.id}"
        cache.set(cache_key, permissions, 300)

        return permissions

    def _get_denied_permissions(self):
        """
        Get explicitly denied permissions for this user.
        These override any granted permissions.

        Returns:
            set: Permission strings that are explicitly denied
        """
        # Placeholder for denied permissions feature
        # Could be implemented as a separate model
        return set()

    def has_permission(
        self, module_slug, permission_codename, force_refresh=False
    ):
        """
        Check if user has a specific permission.

        Args:
            module_slug: Module identifier (e.g., 'students')
            permission_codename: Action (e.g., 'view', 'add')
            force_refresh: Bypass cache

        Returns:
            bool: True if user has permission
        """
        if self.is_superuser:
            return True

        if not self.is_active:
            return False

        # Check for explicit deny first
        denied = self._get_denied_permissions()
        permission_key = build_permission_key(module_slug, permission_codename)
        if permission_key in denied:
            return False

        return has_permission_key(
            self.get_all_permissions(force_refresh),
            module_slug,
            permission_codename,
        )

    def has_any_permission(self, permissions_list, force_refresh=False):
        """
        Check if user has ANY of the specified permissions.

        Args:
            permissions_list: List of tuples [(module_slug, codename), ...]
            force_refresh: Bypass cache

        Returns:
            bool: True if user has at least one permission
        """
        user_perms = self.get_all_permissions(force_refresh)
        for module_slug, codename in permissions_list:
            if has_permission_key(user_perms, module_slug, codename):
                return True
        return False

    def has_all_permissions(self, permissions_list, force_refresh=False):
        """
        Check if user has ALL of the specified permissions.

        Args:
            permissions_list: List of tuples [(module_slug, codename), ...]
            force_refresh: Bypass cache

        Returns:
            bool: True if user has all permissions
        """
        user_perms = self.get_all_permissions(force_refresh)
        for module_slug, codename in permissions_list:
            if not has_permission_key(user_perms, module_slug, codename):
                return False
        return True

    def get_active_roles(self):
        """
        Get all active role assignments for the user.

        Returns:
            QuerySet: Active UserRole assignments
        """
        return (
            self.user_roles.filter(is_active=True, role__is_active=True)
            .filter(
                Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now())
            )
            .select_related("role")
        )

    def get_role_names(self):
        """
        Get names of all active roles.

        Returns:
            list: List of role name strings
        """
        return list(
            self.get_active_roles().values_list("role__name", flat=True)
        )

    def get_modules_with_permissions(self):
        """
        Get all modules with the user's permissions for each.

        Returns:
            dict: {module_name: [permission_names]}
        """
        result = {}
        for perm in self.get_all_permissions():
            parts = perm.rsplit("_", 1)
            if len(parts) == 2:
                module_slug, action = parts
                if module_slug not in result:
                    result[module_slug] = []
                result[module_slug].append(action)
        return result

    def get_highest_priority_role(self):
        """
        Get the highest priority active role.

        Returns:
            Role or None: The role with highest priority
        """
        active_roles = self.get_active_roles()
        if not active_roles.exists():
            return None
        return active_roles.order_by("-role__priority").first().role

    def clear_permission_cache(self):
        """
        Clear the cached permissions for this user.
        Call this when user's roles or permissions change.
        """
        cache_key = f"user_perms_{self.id}"
        cache.delete(cache_key)


class TeacherProfile(models.Model):
    """Extended profile for teachers."""

    DESIGNATION_CHOICES = [
        ("principal", "Principal"),
        ("vice_principal", "Vice Principal"),
        ("head_teacher", "Head Teacher"),
        ("senior_teacher", "Senior Teacher"),
        ("teacher", "Teacher"),
        ("assistant_teacher", "Assistant Teacher"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    employee_id = models.CharField(max_length=50, unique=True)
    designation = models.CharField(
        max_length=20, choices=DESIGNATION_CHOICES, default="teacher"
    )
    qualification = models.TextField(blank=True)
    experience = models.IntegerField(default=0)
    joining_date = models.DateField(null=True, blank=True)
    specializations = models.TextField(blank=True)
    is_class_teacher = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_teacher_profile"
        verbose_name = _("teacher profile")
        verbose_name_plural = _("teacher profiles")

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"


class ParentProfile(models.Model):
    """Extended profile for parents."""

    RELATION_CHOICES = [
        ("father", "Father"),
        ("mother", "Mother"),
        ("guardian", "Guardian"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="parent_profile"
    )
    occupation = models.CharField(max_length=100, blank=True)
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    relation = models.CharField(
        max_length=20, choices=RELATION_CHOICES, default="father"
    )
    emergency_contact = models.CharField(max_length=20, blank=True)
    children = models.ManyToManyField(
        "students.Student", related_name="parents"
    )

    class Meta:
        db_table = "accounts_parent_profile"
        verbose_name = _("parent profile")
        verbose_name_plural = _("parent profiles")

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.relation}"
