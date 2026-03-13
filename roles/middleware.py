from django.utils.deprecation import MiddlewareMixin


class PermissionContextMiddleware(MiddlewareMixin):
    """Attach a permission helper to each request."""

    def process_request(self, request):
        if request.user.is_authenticated:
            request.permission = PermissionContext(request.user)
        else:
            request.permission = AnonymousPermissionContext()


class PermissionContext:
    """Expose permission helpers on the request object."""

    def __init__(self, user):
        self.user = user

    @property
    def permissions(self):
        return self.user.get_all_permissions()

    @property
    def roles(self):
        return self.user.get_role_names()

    def can(self, module, action):
        return self.user.has_permission(module, action)

    def has_role(self, role):
        return role in self.user.get_role_names()

    def can_any(self, *permissions):
        return self.user.has_any_permission(permissions)

    def can_all(self, *permissions):
        return self.user.has_all_permissions(permissions)


class AnonymousPermissionContext:
    """Permission context for unauthenticated users."""

    @property
    def permissions(self):
        return set()

    @property
    def roles(self):
        return []

    def can(self, module, action):
        return False

    def has_role(self, role):
        return False

    def can_any(self, *permissions):
        return False

    def can_all(self, *permissions):
        return False
