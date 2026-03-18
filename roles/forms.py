from django import forms
from django.contrib.auth import get_user_model

from .models import (
    Module,
    PermissionType,
    Role,
    RolePermission,
    UserPermission,
    UserRole,
)
from .services import CORE_PERMISSION_TYPES

User = get_user_model()


class ModuleForm(forms.ModelForm):
    """Form for creating and editing modules."""

    permissions = forms.MultipleChoiceField(
        required=False,
        choices=[
            (code, f"can_{code}")
            for code, _label in CORE_PERMISSION_TYPES
        ],
        widget=forms.CheckboxSelectMultiple,
        label="Permissions",
    )

    class Meta:
        model = Module
        fields = ["name", "slug", "description", "icon", "is_active", "order"]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Module name"}
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "auto-generated if empty",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Module description",
                }
            ),
            "icon": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "fa fa-icon"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "order": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Display order"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["permissions"].initial = list(
                self.instance.permission_types.values_list("codename", flat=True)
            )

    def save(self, commit=True):
        module = super().save(commit=commit)
        if commit:
            self.save_permissions(module)
        return module

    def save_permissions(self, module):
        selected_permissions = set(self.cleaned_data.get("permissions", []))
        existing_permissions = {
            permission.codename: permission
            for permission in module.permission_types.all()
        }

        for order, (code, label) in enumerate(CORE_PERMISSION_TYPES):
            permission = existing_permissions.get(code)
            if code in selected_permissions and permission is None:
                PermissionType.objects.create(
                    module=module,
                    name=label,
                    codename=code,
                    order=order,
                )
            elif code not in selected_permissions and permission is not None:
                permission.delete()


class PermissionTypeForm(forms.ModelForm):
    """Form for creating and editing permission types within a module."""

    class Meta:
        model = PermissionType
        fields = ["module", "name", "codename", "description", "order"]
        widgets = {
            "module": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., View"}
            ),
            "codename": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., view"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        modules = kwargs.pop("modules", None)
        super().__init__(*args, **kwargs)
        if modules is not None:
            self.fields["module"].queryset = modules


class RoleForm(forms.ModelForm):
    """Form for creating and editing roles with permission selection."""

    class Meta:
        model = Role
        fields = [
            "name",
            "description",
            "is_active",
            "is_default",
            "default_for_role",
            "priority",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Role name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Role description",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "is_default": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "default_for_role": forms.Select(
                attrs={"class": "form-select"}
            ),
            "priority": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Higher = more important",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_default = cleaned_data.get("is_default")
        default_for_role = cleaned_data.get("default_for_role")

        if is_default and not default_for_role:
            self.add_error(
                "default_for_role",
                "Please select which user type should receive this default role.",
            )

        if is_default and default_for_role:
            existing_default_roles = Role.objects.filter(
                is_default=True,
                default_for_role=default_for_role,
            )
            if self.instance.pk:
                existing_default_roles = existing_default_roles.exclude(
                    pk=self.instance.pk
                )
            if existing_default_roles.exists():
                self.add_error(
                    "default_for_role",
                    "Only one default role can be set for this user type.",
                )

        if not is_default:
            cleaned_data["default_for_role"] = ""

        return cleaned_data


class RolePermissionForm(forms.Form):
    """Form for selecting permissions when creating/editing a role."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permissions_by_module = {}

        # Get all active modules with their permission types
        modules = Module.objects.filter(is_active=True).prefetch_related(
            "permission_types"
        )
        for module in modules:
            perm_types = module.permission_types.all()
            if perm_types:
                self.permissions_by_module[module] = perm_types

        # Add checkboxes for each permission
        for module, perm_types in self.permissions_by_module.items():
            choices = []
            for pt in perm_types:
                # Find or create RolePermission
                rp, created = RolePermission.objects.get_or_create(
                    module=module, permission_type=pt
                )
                choices.append((rp.id, f"{module.name} - {pt.name}"))

            self.fields[f"module_{module.id}"] = forms.MultipleChoiceField(
                choices=choices,
                required=False,
                widget=forms.CheckboxSelectMultiple,
                label=module.name,
                help_text=module.description,
            )

    def save_permissions(self, role):
        """Save selected permissions to the role."""
        role.permissions.clear()
        for field_name in self.cleaned_data:
            if field_name.startswith("module_"):
                selected_ids = self.cleaned_data[field_name]
                for rp_id in selected_ids:
                    try:
                        rp = RolePermission.objects.get(id=rp_id)
                        role.permissions.add(rp)
                    except RolePermission.DoesNotExist:
                        pass


class UserRoleForm(forms.ModelForm):
    """Form for assigning roles to users."""

    class Meta:
        model = UserRole
        fields = ["user", "role", "expires_at", "is_active"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "expires_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class UserRoleAssignmentForm(forms.Form):
    """Form for assigning multiple roles to a user."""

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Select User",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add checkboxes for each role
        self.fields["roles"] = forms.ModelMultipleChoiceField(
            queryset=Role.objects.filter(is_active=True),
            required=False,
            widget=forms.CheckboxSelectMultiple(
                attrs={"class": "role-checkbox"}
            ),
            label="Assign Roles",
        )
        self.fields["permissions"] = forms.ModelMultipleChoiceField(
            queryset=RolePermission.objects.select_related(
                "module", "permission_type"
            )
            .filter(module__is_active=True)
            .order_by("module__order", "module__name", "permission_type__order"),
            required=False,
            widget=forms.CheckboxSelectMultiple(
                attrs={"class": "permission-checkbox"}
            ),
            label="Assign Direct Permissions",
        )

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        selected_roles = cleaned_data.get("roles", [])
        selected_permissions = cleaned_data.get("permissions", [])

        if not selected_roles and not selected_permissions:
            raise forms.ValidationError(
                "Please select at least one role or direct permission."
            )

        # Check for already active role assignments that would be duplicated
        if user and selected_roles:
            existing_assignments = UserRole.objects.filter(
                user=user, role__in=selected_roles, is_active=True
            ).values_list("role_id", flat=True)

            if existing_assignments:
                existing_role_names = Role.objects.filter(
                    id__in=existing_assignments
                ).values_list("name", flat=True)

                # Add a warning but don't block - we'll handle updates in save()
                self.duplicate_roles = list(existing_role_names)
            else:
                self.duplicate_roles = []
        else:
            self.duplicate_roles = []

        return cleaned_data

    def save(self, assigned_by=None):
        """Save role and direct permission assignments for the selected user."""
        user = self.cleaned_data["user"]
        selected_roles = self.cleaned_data["roles"]
        selected_permissions = self.cleaned_data["permissions"]

        existing_role_ids = list(
            UserRole.objects.filter(user=user).values_list("role_id", flat=True)
        )
        existing_permission_ids = list(
            UserPermission.objects.filter(user=user).values_list(
                "role_permission_id", flat=True
            )
        )

        UserRole.objects.filter(user=user).update(is_active=False)
        UserPermission.objects.filter(user=user).update(is_active=False)

        for role in selected_roles:
            if role.id in existing_role_ids:
                user_role = UserRole.objects.get(user=user, role=role)
                user_role.is_active = True
                user_role.assigned_by = assigned_by
                user_role.save(update_fields=["is_active", "assigned_by"])
            else:
                UserRole.objects.create(
                    user=user,
                    role=role,
                    is_active=True,
                    assigned_by=assigned_by,
                )

        for permission in selected_permissions:
            if permission.id in existing_permission_ids:
                user_permission = UserPermission.objects.get(
                    user=user, role_permission=permission
                )
                user_permission.is_active = True
                user_permission.assigned_by = assigned_by
                user_permission.save(
                    update_fields=["is_active", "assigned_by"]
                )
            else:
                UserPermission.objects.create(
                    user=user,
                    role_permission=permission,
                    is_active=True,
                    assigned_by=assigned_by,
                )

        user.clear_permission_cache()
        return user
