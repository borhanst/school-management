from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.StudentListView.as_view(), name="list"),
    path("add/", views.student_create, name="add"),
    path("<int:pk>/", views.student_detail, name="detail"),
    path("<int:pk>/edit/", views.student_update, name="edit"),
    path("<int:pk>/delete/", views.student_delete, name="delete"),
    path("search/", views.student_search, name="search"),
    path("get-sections/", views.get_sections, name="get_sections"),
    path("promote/", views.student_promote, name="promote"),
    path("promote/history/", views.promotion_history, name="promote_history"),
    path(
        "promote/history/<int:student_id>/",
        views.get_student_promotion_history,
        name="student_promotion_history",
    ),
]
