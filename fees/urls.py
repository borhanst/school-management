from django.urls import path

from . import views

app_name = "fees"

urlpatterns = [
    path("", views.fee_list, name="list"),
    path("create-invoice/", views.create_invoice, name="create_invoice"),
    path("invoice/<int:pk>/edit/", views.edit_invoice, name="edit_invoice"),
    path(
        "invoice/<int:pk>/delete/",
        views.delete_invoice,
        name="delete_invoice",
    ),
    path("payment/", views.payment, name="payment"),
    path("payment/gateway/", views.payment_gateway, name="payment_gateway"),
    path("settings/fee-types/", views.fee_type_list, name="fee_type_list"),
    path(
        "settings/fee-types/add/",
        views.fee_type_create,
        name="fee_type_create",
    ),
    path(
        "settings/fee-types/<int:pk>/edit/",
        views.fee_type_edit,
        name="fee_type_edit",
    ),
    path(
        "settings/fee-types/<int:pk>/delete/",
        views.fee_type_delete,
        name="fee_type_delete",
    ),
    path(
        "settings/fee-structures/",
        views.fee_structure_list,
        name="fee_structure_list",
    ),
    path(
        "settings/fee-structures/add/",
        views.fee_structure_create,
        name="fee_structure_create",
    ),
    path(
        "settings/fee-structures/<int:pk>/edit/",
        views.fee_structure_edit,
        name="fee_structure_edit",
    ),
    path(
        "settings/fee-structures/<int:pk>/delete/",
        views.fee_structure_delete,
        name="fee_structure_delete",
    ),
]
