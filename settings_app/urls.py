from django.urls import path
from . import views

app_name = "settings"

urlpatterns = [
    path("", views.settings_index, name="index"),
    # Academic Year Management
    path("academic-years/", views.academic_year_list, name="academic-year-list"),
    path("academic-years/create/", views.academic_year_create, name="academic-year-create"),
    path("academic-years/<int:pk>/edit/", views.academic_year_edit, name="academic-year-edit"),
    path("academic-years/<int:pk>/delete/", views.academic_year_delete, name="academic-year-delete"),
    # Other Settings
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
