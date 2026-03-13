from django import forms
from django.contrib.auth import get_user_model

from .models import Module, PermissionType, Role, RolePermission, UserRole

User = get_user_model()


class ModuleForm(forms.ModelForm):
    """Form for creating and editing modules."""

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
        fields = ["name", "description", "is_active", "is_default", "priority"]
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
            "priority": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Higher = more important",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group permissions by module for the form
        self.fields["permission_queryset"] = forms.ModelMultipleChoiceField(
            queryset=RolePermission.objects.select_related(
                "module", "permission_type"
            ).all(),
            required=False,
            widget=forms.CheckboxSelectMultiple(
                attrs={"class": "permission-checkbox"}
            ),
            label="Permissions",
        )

    def _init_helper(self):
        """Initialize helper for permissions display."""
        self.permissions_by_module = {}
        all_role_permissions = RolePermission.objects.select_related(
            "module", "permission_type"
        ).all()
        for rp in all_role_permissions:
            module_name = rp.module.name
            if module_name not in self.permissions_by_module:
                self.permissions_by_module[module_name] = []
            self.permissions_by_module[module_name].append(rp)

    def clean(self):
        cleaned_data = super().clean()
        # Handle permissions
        perm_ids = self.data.getlist("permissions")
        cleaned_data["permissions"] = perm_ids
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
            required=True,  # Require at least one role
            widget=forms.CheckboxSelectMultiple(
                attrs={"class": "role-checkbox"}
            ),
            label="Assign Roles",
        )

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        selected_roles = cleaned_data.get("roles", [])

        # Validate that at least one role is selected
        if not selected_roles:
            raise forms.ValidationError(
                "Please select at least one role to assign."
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

        return cleaned_data

    def save(self):
        """Save role assignments for the selected user."""
        user = self.cleaned_data["user"]
        selected_roles = self.cleaned_data["roles"]

        # Get existing role IDs for this user before making changes
        existing_role_ids = list(
            UserRole.objects.filter(user=user).values_list("role_id", flat=True)
        )

        # Deactivate all existing role assignments
        UserRole.objects.filter(user=user).update(is_active=False)

        assigned_roles = []
        for role in selected_roles:
            # Check if this role was previously assigned
            if role.id in existing_role_ids:
                # Re-activate the existing assignment
                user_role = UserRole.objects.get(user=user, role=role)
                user_role.is_active = True
                user_role.save()
            else:
                # Create new assignment
                user_role = UserRole.objects.create(
                    user=user, role=role, is_active=True
                )
            assigned_roles.append(role.name)

        return user
