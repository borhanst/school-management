from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from .forms import (
    ModuleForm,
    PermissionTypeForm,
    RoleForm,
    UserRoleAssignmentForm,
)
from .decorators import PermissionRequiredMixin
from .models import Module, PermissionType, Role, UserRole
from .services import (
    get_role_permission_matrix,
    save_role_permissions,
)

User = get_user_model()


class ManageRolesPermissionMixin(PermissionRequiredMixin):
    """Require the custom permission used for role management."""

    module_slug = "accounts"
    permission_codename = "manage_roles"

    def has_permission(self):
        user = self.request.user
        return (
            user.is_superuser
            or user.role == "admin"
            or user.has_permission(self.module_slug, self.permission_codename)
        )


# ==================== Module Views ====================


class ModuleListView(LoginRequiredMixin, ManageRolesPermissionMixin, ListView):
    """List all modules."""

    model = Module
    template_name = "roles/modules/list.html"
    context_object_name = "modules"
    ordering = ["order", "name"]
    
    def get_queryset(self):
        return Module.objects.prefetch_related("permission_types").order_by(
            "order", "name"
        )


class ModuleCreateView(
    LoginRequiredMixin, ManageRolesPermissionMixin, CreateView
):
    """Create a new module."""

    model = Module
    form_class = ModuleForm
    template_name = "roles/modules/form.html"
    success_url = reverse_lazy("roles:module_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Module created successfully!")
        return response


class ModuleUpdateView(
    LoginRequiredMixin, ManageRolesPermissionMixin, UpdateView
):
    """Update an existing module."""

    model = Module
    form_class = ModuleForm
    template_name = "roles/modules/form.html"
    success_url = reverse_lazy("roles:module_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Module updated successfully!")
        return response


class ModuleDeleteView(
    LoginRequiredMixin, ManageRolesPermissionMixin, DeleteView
):
    """Delete a module."""

    model = Module
    template_name = "roles/modules/confirm_delete.html"
    success_url = reverse_lazy("roles:module_list")

    def form_valid(self, form):
        messages.success(self.request, "Module deleted successfully!")
        return super().form_valid(form)


# ==================== Permission Type Views ====================


class PermissionTypeListView(
    LoginRequiredMixin, ManageRolesPermissionMixin, ListView
):
    """List all permission types."""

    model = PermissionType
    template_name = "roles/permissions/list.html"
    context_object_name = "permission_types"
    ordering = ["module__order", "module__name", "order"]

    def get_queryset(self):
        return PermissionType.objects.select_related("module").order_by(
            "module__order", "module__name", "order"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Group permission types by module
        permission_types = context["permission_types"]
        grouped = {}
        for pt in permission_types:
            module_name = pt.module.name
            if module_name not in grouped:
                grouped[module_name] = []
            grouped[module_name].append(pt)
        context["grouped_permissions"] = grouped
        context["modules"] = Module.objects.filter(is_active=True).order_by(
            "order", "name"
        )
        return context


class PermissionTypeCreateView(
    LoginRequiredMixin, ManageRolesPermissionMixin, CreateView
):
    """Create a new permission type."""

    model = PermissionType
    form_class = PermissionTypeForm
    template_name = "roles/permissions/form.html"

    def get_success_url(self):
        return reverse_lazy("roles:permission_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modules"] = Module.objects.all().order_by("order", "name")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["modules"] = Module.objects.all().order_by("order", "name")
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Permission type created successfully!")
        return super().form_valid(form)


class PermissionTypeUpdateView(
    LoginRequiredMixin, ManageRolesPermissionMixin, UpdateView
):
    """Update an existing permission type."""

    model = PermissionType
    form_class = PermissionTypeForm
    template_name = "roles/permissions/form.html"

    def get_success_url(self):
        return reverse_lazy("roles:permission_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modules"] = Module.objects.all().order_by("order", "name")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["modules"] = Module.objects.all().order_by("order", "name")
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Permission type updated successfully!")
        return super().form_valid(form)


class PermissionTypeDeleteView(
    LoginRequiredMixin, ManageRolesPermissionMixin, DeleteView
):
    """Delete a permission type."""

    model = PermissionType
    template_name = "roles/permissions/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("roles:permission_list")

    def form_valid(self, form):
        messages.success(self.request, "Permission type deleted successfully!")
        return super().form_valid(form)


# ==================== Role Views ====================


class RoleListView(LoginRequiredMixin, ManageRolesPermissionMixin, ListView):
    """List all roles."""

    model = Role
    template_name = "roles/roles/list.html"
    context_object_name = "roles"
    ordering = ["-priority", "name"]


class RoleCreateView(
    LoginRequiredMixin, ManageRolesPermissionMixin, CreateView
):
    """Create a new role."""

    model = Role
    form_class = RoleForm
    template_name = "roles/roles/form.html"
    success_url = reverse_lazy("roles:role_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["permission_matrix"] = get_role_permission_matrix()
        return context

    def form_valid(self, form):
        role = form.save(commit=False)
        role.created_by = self.request.user
        role.save()
        save_role_permissions(role, self.request.POST.getlist("permissions"))

        messages.success(
            self.request, f'Role "{role.name}" created successfully!'
        )
        return redirect(self.success_url)


class RoleUpdateView(
    LoginRequiredMixin, ManageRolesPermissionMixin, UpdateView
):
    """Update an existing role."""

    model = Role
    form_class = RoleForm
    template_name = "roles/roles/form.html"
    success_url = reverse_lazy("roles:role_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["permission_matrix"] = get_role_permission_matrix(
            self.get_object()
        )
        return context

    def form_valid(self, form):
        role = form.save()
        save_role_permissions(role, self.request.POST.getlist("permissions"))

        messages.success(
            self.request, f'Role "{role.name}" updated successfully!'
        )
        return redirect(self.success_url)


class RoleDeleteView(
    LoginRequiredMixin, ManageRolesPermissionMixin, DeleteView
):
    """Delete a role."""

    model = Role
    template_name = "roles/roles/confirm_delete.html"
    success_url = reverse_lazy("roles:role_list")

    def form_valid(self, form):
        role = self.get_object()
        messages.success(
            self.request, f'Role "{role.name}" deleted successfully!'
        )
        return super().form_valid(form)


class RoleDetailView(
    LoginRequiredMixin, ManageRolesPermissionMixin, DetailView
):
    """View role details with permissions."""

    model = Role
    template_name = "roles/roles/detail.html"
    context_object_name = "role"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grouped_permissions = []
        modules = {}

        for permission in context["role"].permissions.select_related(
            "module", "permission_type"
        ).order_by("module__order", "module__name", "permission_type__order"):
            module_id = permission.module_id
            if module_id not in modules:
                modules[module_id] = {
                    "module": permission.module,
                    "permissions": [],
                }
            modules[module_id]["permissions"].append(permission)

        grouped_permissions.extend(modules.values())
        context["grouped_permissions"] = grouped_permissions
        return context


# ==================== User Role Assignment Views ====================


class UserRoleListView(
    LoginRequiredMixin, ManageRolesPermissionMixin, ListView
):
    """List all user role assignments."""

    model = UserRole
    template_name = "roles/assignments/list.html"
    context_object_name = "user_roles"
    ordering = ["-assigned_at"]

    def get_queryset(self):
        return UserRole.objects.select_related(
            "user", "role", "assigned_by"
        ).all()


class UserRoleAssignView(
    LoginRequiredMixin, ManageRolesPermissionMixin, View
):
    """Assign roles to a user."""

    template_name = "roles/assignments/form.html"
    success_url = reverse_lazy("roles:assignment_list")

    def get(self, request, *args, **kwargs):
        form = UserRoleAssignmentForm()
        users = User.objects.all()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "users": users,
                "roles": Role.objects.filter(is_active=True),
                "selected_user_id": None,
            },
        )

    def post(self, request, *args, **kwargs):
        form = UserRoleAssignmentForm(request.POST)
        selected_user_id = request.POST.get("user")
        if form.is_valid():
            user = form.cleaned_data["user"]
            selected_roles = form.cleaned_data.get("roles", [])

            # Update user roles
            UserRole.objects.filter(user=user).update(is_active=False)

            for role in selected_roles:
                user_role, created = UserRole.objects.get_or_create(
                    user=user,
                    role=role,
                    defaults={"assigned_by": request.user, "is_active": True},
                )
                if not created:
                    user_role.is_active = True
                    user_role.assigned_by = request.user
                    user_role.save()

            messages.success(
                request,
                f"Roles assigned to {user.get_full_name() or user.username}!",
            )
            return redirect(self.success_url)

        users = User.objects.all()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "users": users,
                "roles": Role.objects.filter(is_active=True),
                "selected_user_id": selected_user_id,
            },
        )


class UserRoleRemoveView(
    LoginRequiredMixin, ManageRolesPermissionMixin, DeleteView
):
    """Remove a role assignment from a user."""

    model = UserRole
    template_name = "roles/assignments/confirm_delete.html"
    success_url = reverse_lazy("roles:assignment_list")

    def form_valid(self, form):
        user_role = self.get_object()
        messages.success(
            self.request,
            f'Role "{user_role.role.name}" removed from {user_role.user.get_full_name() or user_role.user.username}!',
        )
        return super().form_valid(form)


class UserRoleToggleView(
    LoginRequiredMixin, ManageRolesPermissionMixin, DeleteView
):
    """Toggle a role assignment on/off."""

    def post(self, request, pk):
        user_role = get_object_or_404(UserRole, pk=pk)
        user_role.is_active = not user_role.is_active
        user_role.save()

        status = "activated" if user_role.is_active else "deactivated"
        messages.success(
            request,
            f'Role "{user_role.role.name}" {status} for {user_role.user.get_full_name() or user_role.user.username}!',
        )

        return redirect("roles:assignment_list")
