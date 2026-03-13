from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.template import Context, Template
from django.test import Client, TestCase, override_settings
from django.urls import path, reverse
from django.utils import timezone
from django.views import View

from roles.decorators import PermissionRequiredMixin, permission_required
from roles.middleware import PermissionContext
from roles.models import Module, PermissionType, Role, RolePermission, UserRole
from students.models import AcademicYear, ClassLevel, Section, Student

User = get_user_model()


@permission_required("students", "view")
def protected_function_view(request):
    return HttpResponse("ok")


def resolve_test_module_slug(request, view_func=None):
    return request.GET.get("module")


@permission_required(resolve_test_module_slug, "view")
def protected_dynamic_function_view(request):
    return HttpResponse("ok")


class ProtectedPermissionView(PermissionRequiredMixin, View):
    module_slug = "students"
    permission_codename = "view"

    def get(self, request):
        return HttpResponse("ok")


class DynamicProtectedPermissionView(PermissionRequiredMixin, View):
    permission_codename = "view"

    def get_module_slug(self):
        return self.request.GET.get("module")

    def get(self, request):
        return HttpResponse("ok")


urlpatterns = [
    path("test/protected/", protected_function_view, name="test_protected"),
    path(
        "test/protected-dynamic/",
        protected_dynamic_function_view,
        name="test_protected_dynamic",
    ),
    path("test/protected-cbv/", ProtectedPermissionView.as_view(), name="test_protected_cbv"),
    path(
        "test/protected-cbv-dynamic/",
        DynamicProtectedPermissionView.as_view(),
        name="test_protected_cbv_dynamic",
    ),
]


class PermissionTestMixin:
    def create_permission(self, module_slug, action):
        module, _ = Module.objects.get_or_create(
            slug=module_slug,
            defaults={"name": module_slug.title()},
        )
        permission_type, _ = PermissionType.objects.get_or_create(
            module=module,
            codename=action,
            defaults={"name": action.replace("_", " ").title()},
        )
        role_permission, _ = RolePermission.objects.get_or_create(
            module=module, permission_type=permission_type
        )
        return role_permission

    def assign_permission(self, user, module_slug, action, role_name=None):
        role = Role.objects.create(name=role_name or f"{module_slug}-{action}")
        role.permissions.add(self.create_permission(module_slug, action))
        UserRole.objects.create(user=user, role=role)
        user.clear_permission_cache()
        return role

    def create_user(self, username="user", **kwargs):
        defaults = {
            "password": "pass1234",
            "role": "teacher",
            "is_active": True,
        }
        defaults.update(kwargs)
        password = defaults.pop("password")
        user = User.objects.create_user(
            username=username, password=password, **defaults
        )
        user.clear_permission_cache()
        return user


class PermissionResolutionTests(PermissionTestMixin, TestCase):
    def test_user_permission_resolution_and_superuser_context(self):
        user = self.create_user("teacher1")
        self.assign_permission(user, "students", "view")

        self.assertTrue(user.has_permission("students", "view"))
        self.assertTrue(user.has_any_permission([("students", "view")]))
        self.assertTrue(user.has_all_permissions([("students", "view")]))

        superuser = self.create_user(
            "root", is_superuser=True, is_staff=True, role="admin"
        )
        self.assertTrue(superuser.has_permission("students", "delete"))
        self.assertTrue(PermissionContext(superuser).can("students", "delete"))

    def test_permission_cache_invalidates_when_role_permissions_change(self):
        user = self.create_user("teacher2")
        role = self.assign_permission(
            user, "students", "view", role_name="Teacher Role"
        )

        self.assertEqual(user.get_all_permissions(), {"students_view"})

        role.permissions.add(self.create_permission("students", "edit"))

        self.assertTrue(user.has_permission("students", "edit"))

    def test_expired_and_inactive_assignments_are_ignored(self):
        user = self.create_user("teacher_expired")
        role = Role.objects.create(name="Expired Role")
        role.permissions.add(self.create_permission("students", "view"))

        expired_assignment = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )
        expired_assignment.expires_at = timezone.now() - timedelta(days=1)
        expired_assignment.save(update_fields=["expires_at"])

        self.assertFalse(user.has_permission("students", "view"))

        active_assignment = UserRole.objects.create(
            user=user,
            role=Role.objects.create(name="Active Role"),
            is_active=False,
        )
        active_assignment.role.permissions.add(
            self.create_permission("students", "edit")
        )
        user.clear_permission_cache()

        self.assertFalse(user.has_permission("students", "edit"))


@override_settings(ROOT_URLCONF=__name__)
class PermissionDecoratorTests(PermissionTestMixin, TestCase):
    def setUp(self):
        self.client = Client()

    def test_anonymous_user_is_denied(self):
        response = self.client.get(reverse("test_protected"))
        self.assertEqual(response.status_code, 403)

    def test_user_without_permission_gets_403(self):
        user = self.create_user("teacher3")
        self.assertFalse(user.has_permission("students", "view"))
        self.client.force_login(user)

        response = self.client.get(reverse("test_protected"))
        self.assertEqual(response.status_code, 403)

    def test_user_with_permission_is_allowed(self):
        user = self.create_user("teacher4")
        self.assign_permission(user, "students", "view")
        self.client.force_login(user)

        response = self.client.get(reverse("test_protected"))
        self.assertEqual(response.status_code, 200)

    def test_dynamic_function_view_allows_resolved_active_module(self):
        user = self.create_user("teacher_dynamic_ok")
        self.assign_permission(user, "library", "view")
        self.client.force_login(user)

        response = self.client.get(
            reverse("test_protected_dynamic"), {"module": "library"}
        )
        self.assertEqual(response.status_code, 200)

    def test_dynamic_function_view_denies_unknown_module(self):
        user = self.create_user("teacher_dynamic_unknown")
        self.assign_permission(user, "library", "view")
        self.client.force_login(user)

        response = self.client.get(
            reverse("test_protected_dynamic"), {"module": "unknown-module"}
        )
        self.assertEqual(response.status_code, 403)

    def test_dynamic_function_view_denies_inactive_module(self):
        user = self.create_user("teacher_dynamic_inactive")
        self.assign_permission(user, "library", "view")
        Module.objects.filter(slug="library").update(is_active=False)
        user.clear_permission_cache()
        self.client.force_login(user)

        response = self.client.get(
            reverse("test_protected_dynamic"), {"module": "library"}
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_is_allowed_by_mixin(self):
        user = self.create_user(
            "root2", is_superuser=True, is_staff=True, role="admin"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("test_protected_cbv"))
        self.assertEqual(response.status_code, 200)


class PermissionTemplateTagTests(PermissionTestMixin, TestCase):
    def test_template_filters_support_dot_syntax_and_bad_input(self):
        user = self.create_user("teacher5")
        self.assign_permission(user, "students", "view")

        allowed = Template(
            "{% load permission_tags %}{% if user|has_permission:'students.view' %}yes{% endif %}"
        ).render(Context({"user": user}))
        malformed = Template(
            "{% load permission_tags %}{% if user|has_permission:'badvalue' %}yes{% endif %}"
        ).render(Context({"user": user}))
        anonymous = Template(
            "{% load permission_tags %}{% if user|has_permission:'students.view' %}yes{% endif %}"
        ).render(Context({"user": AnonymousUser()}))

        self.assertEqual(allowed, "yes")
        self.assertEqual(malformed, "")
        self.assertEqual(anonymous, "")

    def test_template_any_all_and_role_tags_use_dynamic_assignments(self):
        user = self.create_user("teacher_tags")
        role = Role.objects.create(name="Attendance Manager")
        role.permissions.add(self.create_permission("students", "view"))
        role.permissions.add(self.create_permission("attendance", "mark"))
        UserRole.objects.create(user=user, role=role)
        user.clear_permission_cache()

        rendered = Template(
            "{% load permission_tags %}"
            "{% if user|has_any_permission:'students.view,fees.view' %}any{% endif %}"
            "{% if user|has_all_permissions:'students.view,attendance.mark' %}all{% endif %}"
            "{% if user|has_role:'Attendance Manager' %}role{% endif %}"
        ).render(Context({"user": user}))

        self.assertIn("any", rendered)
        self.assertIn("all", rendered)
        self.assertIn("role", rendered)

    def test_sidebar_hides_links_without_permission(self):
        user = self.create_user("teacher6")
        self.assign_permission(user, "students", "view")

        rendered = Template(
            "{% include 'partials/sidebar.html' %}"
        ).render(Context({"user": user}))

        self.assertIn("All Students", rendered)
        self.assertNotIn("Exam Schedule", rendered)


class PermissionIntegrationTests(PermissionTestMixin, TestCase):
    def setUp(self):
        self.client = Client()
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(name="Class 1", numeric_name=1)
        self.section = Section.objects.create(
            name="A",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )

    def test_students_list_requires_view_permission(self):
        user = self.create_user("teacher7")
        self.client.force_login(user)
        response = self.client.get(reverse("students:list"))
        self.assertEqual(response.status_code, 403)

        self.assign_permission(user, "students", "view")
        response = self.client.get(reverse("students:list"))
        self.assertEqual(response.status_code, 200)

    def test_student_create_requires_add_permission(self):
        user = self.create_user("teacher8")
        self.client.force_login(user)
        response = self.client.get(reverse("students:add"))
        self.assertEqual(response.status_code, 403)

        self.assign_permission(user, "students", "add")
        response = self.client.get(reverse("students:add"))
        self.assertEqual(response.status_code, 200)

    def test_attendance_ajax_requires_mark_permission(self):
        user = self.create_user("teacher9")
        student_user = self.create_user("student1", role="student")
        Student.objects.create(
            user=student_user,
            admission_no="ADM20250001",
            admission_date=date(2025, 1, 10),
            date_of_birth=date(2015, 1, 1),
            gender="male",
            class_level=self.class_level,
            section=self.section,
            academic_year=self.academic_year,
        )

        self.client.force_login(user)
        response = self.client.get(
            reverse("attendance:get_students"),
            {"section_id": self.section.id},
        )
        self.assertEqual(response.status_code, 403)

        self.assign_permission(user, "attendance", "mark")
        response = self.client.get(
            reverse("attendance:get_students"),
            {"section_id": self.section.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["students"]), 1)

    def test_role_management_bootstrap_access(self):
        admin_user = self.create_user("admin_bootstrap", role="admin")
        self.client.force_login(admin_user)
        response = self.client.get(reverse("roles:role_list"))
        self.assertEqual(response.status_code, 200)

        plain_user = self.create_user("plain_user", role="teacher")
        self.client.force_login(plain_user)
        response = self.client.get(reverse("roles:role_list"))
        self.assertEqual(response.status_code, 403)

        self.assign_permission(
            plain_user, "accounts", "manage_roles", role_name="RBAC Admin"
        )
        response = self.client.get(reverse("roles:role_list"))
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF=__name__)
class PermissionMixinDynamicTests(PermissionTestMixin, TestCase):
    def setUp(self):
        self.client = Client()

    def test_cbv_with_static_module_slug_still_works(self):
        user = self.create_user("teacher_cbv_static")
        self.assign_permission(user, "students", "view")
        self.client.force_login(user)

        response = self.client.get(reverse("test_protected_cbv"))
        self.assertEqual(response.status_code, 200)

    def test_cbv_get_module_slug_allows_resolved_module(self):
        user = self.create_user("teacher_cbv_dynamic")
        self.assign_permission(user, "attendance", "view")
        self.client.force_login(user)

        response = self.client.get(
            reverse("test_protected_cbv_dynamic"), {"module": "attendance"}
        )
        self.assertEqual(response.status_code, 200)

    def test_cbv_get_module_slug_denies_empty_value(self):
        user = self.create_user("teacher_cbv_empty")
        self.assign_permission(user, "attendance", "view")
        self.client.force_login(user)

        response = self.client.get(reverse("test_protected_cbv_dynamic"))
        self.assertEqual(response.status_code, 403)


class PermissionMiddlewareTests(PermissionTestMixin, TestCase):
    def test_permission_context_exposes_live_permissions_and_roles(self):
        user = self.create_user("middleware_user", role="teacher")
        role = Role.objects.create(name="Exam Staff")
        role.permissions.add(self.create_permission("examinations", "view"))
        UserRole.objects.create(user=user, role=role)
        user.clear_permission_cache()

        context = PermissionContext(user)

        self.assertEqual(context.permissions, {"examinations_view"})
        self.assertTrue(context.can("examinations", "view"))
        self.assertFalse(context.can("students", "view"))
        self.assertTrue(context.can_any(("examinations", "view")))
        self.assertTrue(context.can_all(("examinations", "view")))
        self.assertIn("Exam Staff", context.roles)
