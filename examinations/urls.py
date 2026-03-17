from django.urls import path

from . import views

app_name = "examinations"

urlpatterns = [
    path("", views.index, name="index"),
    path("exam-types/create/", views.exam_type_create, name="exam_type_create"),
    path("grades/", views.grades, name="grades"),
    path("grades/entry/", views.grade_entry, name="grade_entry"),
    path("grades/subjects/", views.get_subjects, name="get_subjects"),
    path("grades/students/", views.get_students_for_grade, name="get_students"),
    path("schedule/", views.schedule, name="schedule"),
    path("schedule/add/", views.schedule_add, name="schedule_add"),
    path("schedule/<int:pk>/edit/", views.schedule_edit, name="schedule_edit"),
    path(
        "schedule/<int:pk>/delete/",
        views.schedule_delete,
        name="schedule_delete",
    ),
    path("report-card/", views.report_card, name="report_card"),
    path("my-exams/", views.my_exams, name="my_exams"),
]
