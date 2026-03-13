# Role and Permission Management System Plan - Dynamic RBAC

## Overview
Create a **fully dynamic** Role-Based Access Control (RBAC) system where administrators can create and manage modules through the admin interface. No hardcoded modules or permissions - everything is database-driven and configurable.

**Key Features:**
- One user can have multiple roles
- Dynamic module creation (no hardcoded modules)
- Comprehensive User permission API with class methods

---

## Core Concept
1. **Create custom modules** dynamically
2. **Define permission types** per module
3. **Create roles** with permissions from any module
4. **Assign multiple roles** to users
5. **Use class methods** to check and get user permissions

---

## Models

### 1. Module
```python
class Module(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
```

### 2. PermissionType
```python
class PermissionType(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='permission_types')
    name = models.CharField(max_length=50)
    codename = models.SlugField()
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['module', 'codename']
```

### 3. Role
```python
class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=0)
    permissions = models.ManyToManyField('RolePermission', blank=True, related_name='roles')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 4. RolePermission
```python
class RolePermission(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    permission_type = models.ForeignKey(PermissionType, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['module', 'permission_type']
```

### 5. UserRole
```python
class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
```

---

## User Permission API (Class Methods)

Add these methods to the User model in `accounts/models.py`:

### 1. Get All Permissions (Aggregated from All Roles)
```python
def get_all_permissions(self):
    """
    Get all aggregated permissions from all active roles.
    Returns a set of permission strings: 'module_action'
    Example: {'students_view', 'students_add', 'fees_view'}
    """
    if not self.is_active:
        return set()
    
    permissions = set()
    
    # Check user's direct permissions first (if any)
    for perm in self.user_permissions.all():
        permissions.add(f"{perm.content_type.app_label}_{perm.codename}")
    
    # Aggregate permissions from all active role assignments
    for user_role in self.user_roles.filter(is_active=True, role__is_active=True):
        if user_role.is_expired():
            continue
        for role_perm in user_role.role.permissions.all():
            permissions.add(
                f"{role_perm.module.slug}_{role_perm.permission_type.codename}"
            )
    
    return permissions
```

### 2. Has Specific Permission
```python
def has_permission(self, module_slug, permission_codename):
    """
    Check if user has a specific permission.
    Args:
        module_slug: The module identifier (e.g., 'students', 'fees')
        permission_codename: The action (e.g., 'view', 'add', 'edit', 'delete')
    Returns:
        bool: True if user has permission, False otherwise
    """
    if self.is_superuser:
        return True
    
    if not self.is_active:
        return False
    
    permission_key = f"{module_slug}_{permission_codename}"
    return permission_key in self.get_all_permissions()
```

### 3. Has Any Permission (from list)
```python
def has_any_permission(self, permissions_list):
    """
    Check if user has ANY of the specified permissions.
    Args:
        permissions_list: List of tuples [(module_slug, codename), ...]
    Returns:
        bool: True if user has at least one permission
    """
    user_perms = self.get_all_permissions()
    for module_slug, codename in permissions_list:
        if f"{module_slug}_{codename}" in user_perms:
            return True
    return False
```

### 4. Has All Permissions
```python
def has_all_permissions(self, permissions_list):
    """
    Check if user has ALL of the specified permissions.
    Args:
        permissions_list: List of tuples [(module_slug, codename), ...]
    Returns:
        bool: True if user has all permissions
    """
    user_perms = self.get_all_permissions()
    for module_slug, codename in permissions_list:
        if f"{module_slug}_{codename}" not in user_perms:
            return False
    return True
```

### 5. Get Active Roles
```python
def get_active_roles(self):
    """
    Get all active role assignments for the user.
    Returns:
        QuerySet: Active UserRole assignments
    """
    return self.user_roles.filter(
        is_active=True, 
        role__is_active=True
    ).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=timezone.now())
    )
```

### 6. Get Role Names
```python
def get_role_names(self):
    """
    Get names of all active roles.
    Returns:
        list: List of role name strings
    """
    return list(self.get_active_roles().values_list('role__name', flat=True))
```

### 7. Get Modules with Permissions
```python
def get_modules_with_permissions(self):
    """
    Get all modules with the user's permissions for each.
    Returns:
        dict: {module_name: [permission_names]}
    """
    result = {}
    for perm in self.get_all_permissions():
        parts = perm.rsplit('_', 1)
        if len(parts) == 2:
            module_slug, action = parts
            if module_slug not in result:
                result[module_slug] = []
            result[module_slug].append(action)
    return result
```

### 8. Get Highest Priority Role
```python
def get_highest_priority_role(self):
    """
    Get the highest priority active role.
    Returns:
        Role or None: The role with highest priority
    """
    active_roles = self.get_active_roles().select_related('role')
    if not active_roles.exists():
        return None
    return active_roles.order_by('-role__priority').first().role
```

---

## Usage Examples

### In Views
```python
# Check single permission
if request.user.has_permission('students', 'view'):
    # Show student list

# Check multiple permissions (any)
if request.user.has_any_permission([('students', 'add'), ('students', 'edit')]):
    # Show add/edit buttons

# Check multiple permissions (all)
if request.user.has_all_permissions([('students', 'view'), ('students', 'edit')]):
    # Allow access

# Get user's role names
roles = request.user.get_role_names()

# Get user's modules with permissions
modules = request.user.get_modules_with_permissions()
# Returns: {'students': ['view', 'add', 'edit'], 'fees': ['view', 'add']}
```

### In Templates
```html
{% load permission_tags %}

{% if request.user|has_permission:'students.view' %}
    <a href="{% url 'students:list' %}">View Students</a>
{% endif %}

{% if request.user|has_permission:'students.add' %}
    <a href="{% url 'students:add' %}">Add Student</a>
{% endif %}

{% if request.user|has_any_permission:'students.add,students.edit' %}
    <div>Edit Actions Available</div>
{% endif %}

{% for role in request.user.get_active_roles %}
    <span class="badge">{{ role.role.name }}</span>
{% endfor %}
```

### Template Tags
Create `roles/templatetags/permission_tags.py`:
```python
@register.filter
def has_permission(user, permission_string):
    """Usage: user|has_permission:'module.action'"""
    if not user.is_authenticated:
        return False
    module, action = permission_string.split('.')
    return user.has_permission(module, action)

@register.filter
def has_any_permission(user, permissions_csv):
    """Usage: user|has_any_permission:'module1.action1,module2.action2'"""
    if not user.is_authenticated:
        return False
    perms_list = [tuple(p.split('.')) for p in permissions_csv.split(',')]
    return user.has_any_permission(perms_list)

@register.simple_tag
def get_user_permissions(user):
    """Usage: {% get_user_permissions user as perms %}"""
    return user.get_all_permissions()
```

### In Model Admin
```python
class StudentAdmin(admin.ModelAdmin):
    def has_view_permission(self, request, obj=None):
        return request.user.has_permission('students', 'view')
    
    def has_add_permission(self, request):
        return request.user.has_permission('students', 'add')
    
    def has_change_permission(self, request, obj=None):
        return request.user.has_permission('students', 'edit')
    
    def has_delete_permission(self, request, obj=None):
        return request.user.has_permission('students', 'delete')
```

---

## Default Permission Types per Module

Standard permission types:
- **view** - View/list records
- **add** - Create new records
- **edit** - Modify existing records
- **delete** - Remove records
- **export** - Export data
- **approve** - Approve/reject actions

---

## Acceptance Criteria

1. ✅ One user can have multiple roles
2. ✅ Dynamic module creation
3. ✅ Custom permission types per module
4. ✅ get_all_permissions() method returns aggregated permissions
5. ✅ has_permission(module, action) method for checking
6. ✅ has_any_permission() and has_all_permissions() methods
7. ✅ get_active_roles() method
8. ✅ Template tags for permission checking
9. ✅ Works with Django admin
10. ✅ Clean UI for management
