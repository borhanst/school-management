from django.http import JsonResponse
from django.urls import path

app_name = "communications"

urlpatterns = [
    path("", lambda r: JsonResponse({"status": "ok"}), name="index"),
    path(
        "messages/", lambda r: JsonResponse({"status": "ok"}), name="messages"
    ),
    path("notices/", lambda r: JsonResponse({"status": "ok"}), name="notices"),
]
