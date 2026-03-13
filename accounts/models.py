from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom User model using the built-in role field only."""

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

    # ==================== Compatibility Permission Methods ====================

    def get_all_permissions(self, force_refresh=False):
        """Get all effective permissions from active role assignments."""
        if not self.is_active:
            return set()
        if self.is_superuser:
            return {"*"}

        cache_key = f"user_perms_{self.id}"
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        permissions = set()
        active_roles = self.get_active_roles().prefetch_related(
            "role__permissions__module", "role__permissions__permission_type"
        )

        for user_role in active_roles:
            for role_permission in user_role.role.permissions.all():
                if not role_permission.module.is_active:
                    continue
                permissions.add(role_permission.codename)

        cache.set(cache_key, permissions, 300)
        return permissions

    def _get_denied_permissions(self):
        """Reserved for future explicit deny rules."""
        return set()

    def has_permission(
        self, module_slug, permission_codename, force_refresh=False
    ):
        if self.is_superuser:
            return True
        if not self.is_active:
            return False

        permission_key = f"{module_slug}_{permission_codename}"
        if permission_key in self._get_denied_permissions():
            return False

        return permission_key in self.get_all_permissions(
            force_refresh=force_refresh
        )

    def has_any_permission(self, permissions_list, force_refresh=False):
        if self.is_superuser:
            return True
        if not self.is_active:
            return False

        user_perms = self.get_all_permissions(force_refresh=force_refresh)
        for module_slug, permission_codename in permissions_list:
            if f"{module_slug}_{permission_codename}" in user_perms:
                return True
        return False

    def has_all_permissions(self, permissions_list, force_refresh=False):
        if self.is_superuser:
            return True
        if not self.is_active:
            return False

        user_perms = self.get_all_permissions(force_refresh=force_refresh)
        for module_slug, permission_codename in permissions_list:
            if f"{module_slug}_{permission_codename}" not in user_perms:
                return False
        return True

    def get_active_roles(self):
        """Return active, non-expired dynamic role assignments."""
        return (
            self.user_roles.filter(is_active=True, role__is_active=True)
            .filter(
                Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now())
            )
            .select_related("role")
        )

    def get_role_names(self):
        """Return active dynamic role names plus the built-in profile role."""
        if not self.is_active:
            return []

        role_names = list(
            self.get_active_roles().values_list("role__name", flat=True)
        )
        if self.role and self.role not in role_names:
            role_names.append(self.role)
        return role_names

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
        """Return the highest-priority active dynamic role."""
        active_roles = self.get_active_roles().order_by("-role__priority")
        assignment = active_roles.first()
        return assignment.role if assignment else None

    def clear_permission_cache(self):
        """Clear cached effective permissions for this user."""
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
