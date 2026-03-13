from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.decorators import method_decorator

from .models import Module


def _compute_module_slug(module_slug, request, view_func=None, view_instance=None):
    """Resolve a module slug from a literal value or callable."""
    if callable(module_slug):
        if view_instance is not None:
            resolved = module_slug(view_instance, request)
        elif view_func is not None:
            resolved = module_slug(request, view_func=view_func)
        else:
            resolved = module_slug(request)
    else:
        resolved = module_slug

    if resolved is None:
        return None

    resolved = str(resolved).strip()
    if not resolved:
        return None

    return resolved


def _resolve_module_slug(module_slug, request, view_func=None, view_instance=None):
    """Resolve and validate a module slug for non-superuser checks."""
    resolved = _compute_module_slug(
        module_slug, request, view_func=view_func, view_instance=view_instance
    )
    if not resolved:
        return None

    exists = Module.objects.filter(slug=resolved, is_active=True).exists()
    if not exists:
        return None

    return resolved


def _permission_denied_response(request, message, redirect_url=None):
    """Return a consistent permission denied response with a flash message."""
    messages.error(request, message)
    if redirect_url:
        return redirect(redirect_url)
    return HttpResponseForbidden("Permission denied.")


def permission_required(
    module_slug,
    permission_codename,
    login_url=None,
    redirect_url=None,
    message=None,
):
    """
    Decorator to check if user has a specific permission.

    Usage:
        @permission_required('students', 'view')
        def my_view(request):
            ...

    Args:
        module_slug: Module identifier (e.g., 'students')
        permission_codename: Action (e.g., 'view', 'add', 'edit')
        login_url: URL to redirect unauthenticated users
        redirect_url: URL to redirect after denied access (default: previous page)
        message: Custom error message to display
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            resolved_module_slug = _compute_module_slug(
                module_slug, request, view_func=view_func
            )
            if request.user.is_superuser:
                if resolved_module_slug and request.user.has_permission(
                    resolved_module_slug, permission_codename
                ):
                    return view_func(request, *args, **kwargs)
            else:
                resolved_module_slug = _resolve_module_slug(
                    module_slug, request, view_func=view_func
                )
                if resolved_module_slug and request.user.has_permission(
                    resolved_module_slug, permission_codename
                ):
                    return view_func(request, *args, **kwargs)

            # Permission denied - show message and redirect
            denied_message = message or (
                "You don't have permission to "
                f"{permission_codename} {resolved_module_slug or 'this module'}."
            )
            return _permission_denied_response(
                request, denied_message, redirect_url
            )

        return _wrapped

    return decorator


def permission_required_any(*permissions, **kwargs):
    """
    Decorator to check if user has ANY of the specified permissions.

    Usage:
        @permission_required_any(('students', 'view'), ('students', 'add'))
        def my_view(request):
            ...

    Args:
        permissions: Tuple of (module_slug, permission_codename)
        login_url: URL to redirect unauthenticated users
        message: Custom error message to display
    """
    login_url = kwargs.get("login_url")
    message = kwargs.get("message")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            if request.user.has_any_permission(permissions):
                return view_func(request, *args, **kwargs)

            denied_message = message or (
                "You don't have any of the required permissions."
            )
            return _permission_denied_response(request, denied_message)

        return _wrapped

    return decorator


def permission_required_all(*permissions, **kwargs):
    """
    Decorator to check if user has ALL of the specified permissions.

    Usage:
        @permission_required_all(('students', 'view'), ('students', 'edit'), ('students', 'delete'))
        def manage_students(request):
            ...

    Args:
        permissions: Tuple of (module_slug, permission_codename)
        login_url: URL to redirect unauthenticated users
        message: Custom error message to display
    """
    login_url = kwargs.get("login_url")
    message = kwargs.get("message")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            if request.user.has_all_permissions(permissions):
                return view_func(request, *args, **kwargs)

            denied_message = message or "You don't have all required permissions."
            return _permission_denied_response(request, denied_message)

        return _wrapped

    return decorator


def role_required(role_name, **kwargs):
    """
    Decorator to check if user has a specific role.

    Usage:
        @role_required('admin')
        def my_view(request):
            ...

    Args:
        role_name: Name of the role to check
        login_url: URL to redirect unauthenticated users
        message: Custom error message to display
    """
    login_url = kwargs.get("login_url")
    message = kwargs.get("message")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            if role_name in request.user.get_role_names():
                return view_func(request, *args, **kwargs)

            denied_message = message or (
                f"You must be a {role_name} to access this page."
            )
            return _permission_denied_response(request, denied_message)

        return _wrapped

    return decorator


def permission_or_role_required(permission=None, role=None, **kwargs):
    """
    Decorator to check if user has permission OR a specific role.
    Useful for allowing either specific permission or a privileged role.

    Usage:
        @permission_or_role_required(permission=('students', 'view'), role='admin')
        def my_view(request):
            ...
    """
    login_url = kwargs.get("login_url")
    message = kwargs.get("message")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            has_perm = False
            has_role = False

            if permission:
                has_perm = request.user.has_permission(
                    permission[0], permission[1]
                )

            if role:
                has_role = role in request.user.get_role_names()

            if has_perm or has_role:
                return view_func(request, *args, **kwargs)

            denied_message = message or "You don't have the required access."
            return _permission_denied_response(request, denied_message)

        return _wrapped

    return decorator


def class_permission_required(module_slug, permission_codename):
    """
    Decorator for class-based views to check permission.

    Usage:
        @method_decorator(class_permission_required('students', 'view'), name='dispatch')
        class StudentListView(View):
            ...
    """
    return method_decorator(
        permission_required(module_slug, permission_codename), name="dispatch"
    )


def class_permission_required_any(*permissions):
    """Decorator for class-based views to check any permission."""
    return method_decorator(
        permission_required_any(*permissions), name="dispatch"
    )


def class_permission_required_all(*permissions):
    """Decorator for class-based views to check all permissions."""
    return method_decorator(
        permission_required_all(*permissions), name="dispatch"
    )


def class_role_required(role_name):
    """Decorator for class-based views to check role."""
    return method_decorator(role_required(role_name), name="dispatch")


class PermissionRequiredMixin(AccessMixin):
    """Declarative permission checks for class-based views."""

    module_slug = None
    permission_codename = None
    permission_denied_message = None

    def get_module_slug(self):
        """Return the configured module slug for this view."""
        return self.module_slug

    def get_required_permission(self):
        module_slug = _compute_module_slug(
            self.get_module_slug(), self.request, view_instance=self
        )
        if not module_slug or not self.permission_codename:
            raise ValueError(
                "PermissionRequiredMixin requires module_slug and permission_codename."
            )
        return module_slug, self.permission_codename

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        self.request = request
        resolved_module_slug = _compute_module_slug(
            self.get_module_slug(), request, view_instance=self
        )
        validated_module_slug = resolved_module_slug
        if not request.user.is_superuser:
            validated_module_slug = _resolve_module_slug(
                self.get_module_slug(), request, view_instance=self
            )

        if (
            validated_module_slug
            and self.permission_codename
            and request.user.has_permission(
                validated_module_slug, self.permission_codename
            )
        ):
            return super().dispatch(request, *args, **kwargs)

        denied_message = self.permission_denied_message or (
            "You don't have permission to "
            f"{self.permission_codename} {resolved_module_slug or 'this module'}."
        )
        return _permission_denied_response(request, denied_message)
