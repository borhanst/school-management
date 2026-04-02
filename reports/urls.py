from django.urls import path

from core.views import ComingSoonView

app_name = "reports"

urlpatterns = [
    path("", ComingSoonView.as_view(
        module_name="Reports",
        module_icon="fa-chart-pie",
        description="Reports module is under development. Soon you'll be able to generate and view comprehensive reports."
    ), name="index"),
    path("student/", ComingSoonView.as_view(
        module_name="Student Reports",
        module_icon="fa-user-graduate",
        description="Student reporting is under development. Soon you'll be able to view detailed student performance reports."
    ), name="student"),
    path(
        "attendance/",
        ComingSoonView.as_view(
            module_name="Attendance Reports",
            module_icon="fa-calendar-check",
            description="Attendance reporting is under development. Soon you'll be able to analyze attendance patterns."
        ),
        name="attendance",
    ),
    path("fees/", ComingSoonView.as_view(
        module_name="Fee Reports",
        module_icon="fa-dollar-sign",
        description="Fee collection reporting is under development. Soon you'll be able to track and analyze fee payments."
    ), name="fees"),
]
