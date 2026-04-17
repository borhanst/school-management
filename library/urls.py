from django.urls import path

from core.views import ComingSoonView
from library import views

app_name = "library"

urlpatterns = [
    path("", views.library_index, name="index"),
    path("books/", views.book_list, name="books"),
    path(
        "issue-book/",
        ComingSoonView.as_view(
            module_name="Library",
            module_icon="fa-book-reader",
            description="Library management module is under development. Soon you'll be able to manage books, issue/return books, and track library activities."
        ),
        name="issue_book",
    ),
]
