from django.http import JsonResponse
from django.urls import path

app_name = "reports"

urlpatterns = [
    path("", lambda r: JsonResponse({"status": "ok"}), name="index"),
    path("student/", lambda r: JsonResponse({"status": "ok"}), name="student"),
    path(
        "attendance/",
        lambda r: JsonResponse({"status": "ok"}),
        name="attendance",
    ),
    path("fees/", lambda r: JsonResponse({"status": "ok"}), name="fees"),
]
