from django.http import JsonResponse
from django.urls import path

app_name = "library"

urlpatterns = [
    path("", lambda r: JsonResponse({"status": "ok"}), name="index"),
    path("books/", lambda r: JsonResponse({"status": "ok"}), name="books"),
    path(
        "issue-book/",
        lambda r: JsonResponse({"status": "ok"}),
        name="issue_book",
    ),
]
