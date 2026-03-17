from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path(
        "",
        lambda request: __import__(
            "django.http",
            fromlist=["JsonResponse"],
            globals={
                "JsonResponse": __import__(
                    "django.http", fromlist=["JsonResponse"]
                ).JsonResponse
            },
        ).JsonResponse({"status": "ok"}),
        name="index",
    ),
    path("classes/", views.classes, name="classes"),
    path("classes/create/", views.class_create, name="class_create"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("sections/create/", views.section_create, name="section_create"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),
    path("subjects/", views.subjects, name="subjects"),
    path("subjects/create/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),
    path("timetable/", views.timetable_view, name="timetable"),
    path("timetable/create/", views.timetable_create, name="timetable_create"),
    path("timetable/<int:pk>/edit/", views.timetable_edit, name="timetable_edit"),
    path("timetable/<int:pk>/delete/", views.timetable_delete, name="timetable_delete"),
    path("my-class/", views.my_class, name="my_class"),
]
