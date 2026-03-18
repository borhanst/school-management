from django.http import JsonResponse
from django.urls import path

from . import views

app_name = "communications"

urlpatterns = [
    path("", lambda r: JsonResponse({"status": "ok"}), name="index"),
    path(
        "messages/", lambda r: JsonResponse({"status": "ok"}), name="messages"
    ),
    path("notices/", views.notice_list, name="notices"),
]
