from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.index, name="index"),
    path("mark/", views.mark_attendance, name="mark"),
    path("save/", views.save_attendance, name="save"),
    path("report/", views.attendance_report, name="report"),
    path("students/", views.get_students, name="get_students"),
    path("leave/", views.leave_request_list, name="leave_requests"),
    path("leave/add/", views.leave_request_create, name="leave_request_add"),
    path(
        "leave/<int:pk>/approve/",
        views.leave_request_approve,
        name="leave_request_approve",
    ),
    path(
        "leave/<int:pk>/reject/",
        views.leave_request_reject,
        name="leave_request_reject",
    ),
    path("my/", views.my_attendance, name="my_attendance"),
]
