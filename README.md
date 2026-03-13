# School Management System

## Custom Permission Convention

- Use `request.user.has_permission(module, action)` and `request.permission.can(module, action)` as the canonical runtime checks.
- Use decorators or `PermissionRequiredMixin` for view protection; do not rely on `user.role` for normal business access.
- Use `view`, `add`, `edit`, and `delete` as the standard CRUD codenames.
- Use module-specific codenames only for non-CRUD actions such as `students.promote`, `attendance.mark`, `attendance.view_reports`, and `accounts.manage_roles`.
- In templates, prefer:
  - `user|has_permission:"students.view"`
  - `user|has_any_permission:"students.view,students.add"`
  - `{% get_user_permissions user as perms %}` when a template performs many checks
