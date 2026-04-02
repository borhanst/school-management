# AGENTS.md - School Management System (SMS)

## Project Overview

Django-based School Management System with custom RBAC permission system. Uses `uv` for package management and SQLite for development.

**Stack:** Django 5.2, Python 3.11, HTMX, Alpine.js, Tailwind CSS

## Commands

### Setup
```bash
uv sync                    # Install dependencies
uv run python manage.py migrate  # Run migrations
uv run python manage.py createsuperuser  # Create admin user
```

### Development
```bash
uv run python manage.py runserver  # Start dev server
uv run python manage.py makemigrations  # Create migrations
uv run python manage.py migrate  # Apply migrations
```

### Testing
```bash
uv run python manage.py test  # Run all tests
uv run python manage.py test students  # Test specific app
uv run python manage.py test students.tests  # Test specific module
uv run python manage.py test roles.tests.PermissionResolutionTests  # Test specific class
uv run python manage.py test roles.tests.PermissionResolutionTests.test_user_permission_resolution_and_superuser_context  # Single test
```

### Management
```bash
uv run python manage.py shell  # Django shell
uv run python manage.py dbshell  # Database shell
uv run python manage.py show_urls  # Show URL patterns (if available)
uv run python manage.py create_fixed_modules  # Create default permission modules
```

## Code Style & Conventions

### Imports
- Standard library imports first, then third-party, then local apps
- Use absolute imports: `from students.models import Student`
- Group imports with blank line separator between groups
- Use `from django.utils.translation import gettext_lazy as _` for translatable strings

### Models
- Use explicit `db_table` in Meta class: `db_table = "students_promotion_history"`
- Define `verbose_name` and `verbose_name_plural` in Meta
- Use `ordering` in Meta where appropriate
- Use `related_name` on all ForeignKey/ManyToMany fields
- Custom User model extends `AbstractUser` (located in `accounts.models.User`)
- Use `AUTH_USER_MODEL = "accounts.User"` for foreign key references

### Views
- Use function-based views with `@login_required` and `@permission_required` decorators
- For class-based views, inherit from `PermissionRequiredMixin` for permission checks
- Use `get_object_or_404` for object retrieval
- Return `JsonResponse` for AJAX/HTMX requests
- Use `messages` framework for user feedback

### Permissions (Critical Convention)
- Use `request.user.has_permission(module, action)` for permission checks
- Use `request.permission.can(module, action)` in templates via middleware context
- Standard CRUD codenames: `view`, `add`, `edit`, `delete`
- Module-specific codenames for special actions: `students.promote`, `attendance.mark`
- Decorators: `@permission_required(module, action)`, `@permission_or_role_required()`
- Template filters: `user|has_permission:"students.view"`, `user|has_any_permission:"students.view,students.add"`

### URL Naming
- Use namespaced URLs: `app_name = "students"` in urls.py
- Reference URLs with namespace: `reverse("students:list")`
- URL patterns use trailing slashes

### Forms
- Use Django ModelForms where appropriate
- Define `Meta.model` and `Meta.fields` explicitly
- Custom validation in `clean_<fieldname>()` methods

### Templates
- Template directory: `templates/` at project root
- App-specific templates in app directories
- Use `{% load permission_tags %}` for permission checks
- HTMX patterns: `hx-get`, `hx-post`, `hx-target`, `hx-swap`
- Alpine.js for client-side state: `x-data`, `x-show`, `@click`

### Error Handling
- Use Django's `messages` framework for user-facing errors
- Return appropriate HTTP status codes (403 for permission denied, 404 for not found)
- Use `try/except IntegrityError` for database constraint violations
- Wrap database modifications in `transaction.atomic()`

### Naming Conventions
- Models: PascalCase (`StudentPromotionHistory`)
- Functions/variables: snake_case (`generate_admission_no`)
- URL names: lowercase with hyphens (`student-detail`)
- Template files: lowercase with underscores (`student_list.html`)

### Database
- Development: SQLite (`db.sqlite3`)
- Production: PostgreSQL (per SPEC.md)
- Timezone: `Asia/Dhaka`
- Pagination: 20 items per page

## Testing Conventions
- Use Django's `TestCase` class
- Test files: `<app>/tests.py`
- Test class naming: `<Feature>Tests` (e.g., `PermissionResolutionTests`)
- Test method naming: `test_<what_it_does>` (e.g., `test_user_with_permission_is_allowed`)
- Use `self.client.force_login(user)` for authentication in tests
- Create helper methods in test classes using mixins (see `PermissionTestMixin`)
- Use `@override_settings(ROOT_URLCONF=__name__)` for testing URL patterns defined in test file

## Architecture Notes
- Custom permission system in `roles` app (not Django's built-in permissions)
- Permission resolution: User -> UserRole -> Role -> RolePermission -> Module + PermissionType
- Direct user permissions supported via `UserPermission` model
- Permission caching with `user.clear_permission_cache()` after changes
- Middleware: `PermissionContextMiddleware` exposes `request.permission`
- Session timeout: 24 hours
