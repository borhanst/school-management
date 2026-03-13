"""
Middleware for adding permission context to requests.
"""

from django.utils.deprecation import MiddlewareMixin

from .permissions import has_permission_key


class PermissionContextMiddleware(MiddlewareMixin):
    """
    Middleware to add permission context to request.
    Provides quick access to common permission checks via request.permission.

    Usage in views:
        # Quick permission check
        if request.permission.can('students', 'view'):
            ...

        # Quick role check
        if request.permission.is('admin'):
            ...

        # Access cached permissions
        permissions = request.permission.permissions

        # Access role names
        roles = request.permission.roles
    """

    def process_request(self, request):
        # Add permission helper to authenticated users
        if request.user.is_authenticated:
            request.permission = PermissionContext(request.user)
        else:
            request.permission = AnonymousPermissionContext()


class PermissionContext:
    """Quick permission checking helper attached to request."""

    def __init__(self, user):
        self.user = user
        self._permissions = None
        self._roles = None

    @property
    def permissions(self):
        """Get all cached permissions for the user."""
        if self._permissions is None:
            self._permissions = self.user.get_all_permissions()
        return self._permissions

    @property
    def roles(self):
        """Get all role names for the user."""
        if self._roles is None:
            self._roles = self.user.get_role_names()
        return self._roles

    def can(self, module, action):
        """
        Quick check if user has permission.

        Args:
            module: Module slug (e.g., 'students')
            action: Action (e.g., 'view')

        Returns:
            bool: True if user has permission
        """
        return has_permission_key(self.permissions, module, action)

    def has_role(self, role):
        """
        Quick check if user has specific role.

        Args:
            role: Role name (e.g., 'admin')

        Returns:
            bool: True if user has the role
        """
        return role in self.roles

    def can_any(self, *permissions):
        """
        Quick check if user has any of the specified permissions.

        Args:
            permissions: Tuples of (module, action)

        Returns:
            bool: True if user has at least one permission
        """
        for module, action in permissions:
            if self.can(module, action):
                return True
        return False

    def can_all(self, *permissions):
        """
        Quick check if user has all of the specified permissions.

        Args:
            permissions: Tuples of (module, action)

        Returns:
            bool: True if user has all permissions
        """
        for module, action in permissions:
            if not self.can(module, action):
                return False
        return True


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
        return True  # Empty set of requirements is satisfied
