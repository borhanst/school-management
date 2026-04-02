from django.urls import path
from . import views

app_name = "settings"

urlpatterns = [
    path("", views.settings_index, name="index"),
    path("school-info/", views.school_info_settings, name="school-info"),
    path("academic/", views.academic_settings, name="academic"),
    path("grading/", views.grading_settings, name="grading"),
    path("attendance/", views.attendance_settings, name="attendance"),
    path("examination/", views.examination_settings, name="examination"),
    path("promotion/", views.promotion_settings, name="promotion"),
    path("student/", views.student_settings, name="student"),
    path("fee/", views.fee_settings, name="fee"),
    path("library/", views.library_settings, name="library"),
    path("transport/", views.transport_settings, name="transport"),
    path("report-card/", views.report_card_settings, name="report-card"),
]
