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
    path("subjects/", views.subjects, name="subjects"),
    path("timetable/", views.timetable_view, name="timetable"),
    path("my-class/", views.my_class, name="my_class"),
]
