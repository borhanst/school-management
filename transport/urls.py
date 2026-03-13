from django.http import JsonResponse
from django.urls import path

app_name = "transport"

urlpatterns = [
    path("", lambda r: JsonResponse({"status": "ok"}), name="index"),
    path("routes/", lambda r: JsonResponse({"status": "ok"}), name="routes"),
]
