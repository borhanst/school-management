from django.urls import path

from . import views

app_name = "roles"

urlpatterns = [
    # Module URLs
    path("modules/", views.ModuleListView.as_view(), name="module_list"),
    path(
        "modules/create/",
        views.ModuleCreateView.as_view(),
        name="module_create",
    ),
    path(
        "modules/<int:pk>/edit/",
        views.ModuleUpdateView.as_view(),
        name="module_edit",
    ),
    path(
        "modules/<int:pk>/delete/",
        views.ModuleDeleteView.as_view(),
        name="module_delete",
    ),
    # Permission Type URLs
    path(
        "permissions/",
        views.PermissionTypeListView.as_view(),
        name="permission_list",
    ),
    path(
        "permissions/create/",
        views.PermissionTypeCreateView.as_view(),
        name="permission_create",
    ),
    path(
        "permissions/<int:pk>/edit/",
        views.PermissionTypeUpdateView.as_view(),
        name="permission_edit",
    ),
    path(
        "permissions/<int:pk>/delete/",
        views.PermissionTypeDeleteView.as_view(),
        name="permission_delete",
    ),
    # Role URLs
    path("roles/", views.RoleListView.as_view(), name="role_list"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role_create"),
    path("roles/<int:pk>/", views.RoleDetailView.as_view(), name="role_detail"),
    path(
        "roles/<int:pk>/edit/", views.RoleUpdateView.as_view(), name="role_edit"
    ),
    path(
        "roles/<int:pk>/delete/",
        views.RoleDeleteView.as_view(),
        name="role_delete",
    ),
    # User Role Assignment URLs
    path(
        "assignments/", views.UserRoleListView.as_view(), name="assignment_list"
    ),
    path(
        "assignments/assign/",
        views.UserRoleAssignView.as_view(),
        name="assign_role",
    ),
    path(
        "assignments/<int:pk>/remove/",
        views.UserRoleRemoveView.as_view(),
        name="remove_role",
    ),
    path(
        "assignments/<int:pk>/toggle/",
        views.UserRoleToggleView.as_view(),
        name="toggle_role",
    ),
    path(
        "direct-permissions/<int:pk>/remove/",
        views.UserPermissionRemoveView.as_view(),
        name="remove_direct_permission",
    ),
    path(
        "direct-permissions/<int:pk>/toggle/",
        views.UserPermissionToggleView.as_view(),
        name="toggle_direct_permission",
    ),
]
