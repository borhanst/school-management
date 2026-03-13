from django.http import JsonResponse
from django.urls import path

app_name = "fees"

urlpatterns = [
    path("", lambda r: JsonResponse({"status": "ok"}), name="list"),
    path(
        "create-invoice/",
        lambda r: JsonResponse({"status": "ok"}),
        name="create_invoice",
    ),
    path("payment/", lambda r: JsonResponse({"status": "ok"}), name="payment"),
]
