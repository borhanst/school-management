from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.decorators import method_decorator


def _permission_denied_response(request, message, redirect_url=None):
    """Return a consistent denied response with a flash message."""
    messages.error(request, message)
    if redirect_url:
        return redirect(redirect_url)
    return HttpResponseForbidden("Permission denied.")


def _resolve_module_slug(module_slug, request, view_instance=None):
    """Resolve a static or callable module slug."""
    if callable(module_slug):
        if view_instance is not None:
            return module_slug(request, view_instance)
        return module_slug(request)
    return module_slug


def permission_required(
    module_slug,
    permission_codename,
    login_url=None,
    redirect_url=None,
    message=None,
):
    """Require a specific module/action permission."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            resolved_module = _resolve_module_slug(module_slug, request)
            if request.user.has_permission(
                resolved_module, permission_codename
            ):
                return view_func(request, *args, **kwargs)

            denied_message = (
                message
                or f"You don't have permission to {permission_codename} {resolved_module}."
            )
            return _permission_denied_response(
                request, denied_message, redirect_url=redirect_url
            )

        return _wrapped

    return decorator


def permission_required_any(*permissions, **kwargs):
    """Require any permission from the provided list."""
    login_url = kwargs.get("login_url")
    redirect_url = kwargs.get("redirect_url")
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

            denied_message = (
                message or "You don't have any of the required permissions."
            )
            return _permission_denied_response(
                request, denied_message, redirect_url=redirect_url
            )

        return _wrapped

    return decorator


def permission_required_all(*permissions, **kwargs):
    """Require all permissions from the provided list."""
    login_url = kwargs.get("login_url")
    redirect_url = kwargs.get("redirect_url")
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

            denied_message = (
                message or "You don't have all of the required permissions."
            )
            return _permission_denied_response(
                request, denied_message, redirect_url=redirect_url
            )

        return _wrapped

    return decorator


def role_required(role_name, **kwargs):
    """Role check using dynamic assignments with built-in role fallback."""
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
    """Allow access by either permission or role."""
    login_url = kwargs.get("login_url")
    redirect_url = kwargs.get("redirect_url")
    message = kwargs.get("message")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return HttpResponseForbidden("Authentication required.")

            if permission is None and role is None:
                return view_func(request, *args, **kwargs)

            if permission is not None:
                module_slug, permission_codename = permission
                if request.user.has_permission(
                    module_slug, permission_codename
                ):
                    return view_func(request, *args, **kwargs)

            if role and role in request.user.get_role_names():
                return view_func(request, *args, **kwargs)

            denied_message = message or "You don't have the required access."
            return _permission_denied_response(
                request, denied_message, redirect_url=redirect_url
            )

        return _wrapped

    return decorator


def class_permission_required(module_slug, permission_codename):
    return method_decorator(
        permission_required(module_slug, permission_codename), name="dispatch"
    )


def class_permission_required_any(*permissions):
    return method_decorator(
        permission_required_any(*permissions), name="dispatch"
    )


def class_permission_required_all(*permissions):
    return method_decorator(
        permission_required_all(*permissions), name="dispatch"
    )


def class_role_required(role_name):
    return method_decorator(role_required(role_name), name="dispatch")


class PermissionRequiredMixin(AccessMixin):
    """Class-based view mixin for permission enforcement."""

    module_slug = None
    permission_codename = None
    permission_denied_message = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        module_slug = self.get_module_slug()
        permission_codename = self.get_permission_codename()
        if not permission_codename:
            raise AttributeError(
                "PermissionRequiredMixin requires module_slug and permission_codename."
            )
        if not module_slug:
            denied_message = (
                self.permission_denied_message
                or "You don't have permission to access this page."
            )
            return _permission_denied_response(request, denied_message)

        if self.has_permission():
            return super().dispatch(request, *args, **kwargs)

        denied_message = (
            self.permission_denied_message
            or f"You don't have permission to {permission_codename} {module_slug}."
        )
        return _permission_denied_response(request, denied_message)

    def get_module_slug(self):
        return self.module_slug

    def get_permission_codename(self):
        return self.permission_codename

    def has_permission(self):
        module_slug = self.get_module_slug()
        permission_codename = self.get_permission_codename()
        return self.request.user.has_permission(
            module_slug, permission_codename
        )
