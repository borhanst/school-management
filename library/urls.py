from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.library_index, name="index"),
    path("books/", views.book_list, name="books"),
    path(
        "issue-book/",
        views.book_list,
        name="issue_book",
    ),
]
