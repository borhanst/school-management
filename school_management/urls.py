"""
URL configuration for school_management project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Accounts
    path("accounts/", include("accounts.urls", namespace="accounts")),
    # Roles
    path("roles/", include("roles.urls", namespace="roles")),
    # Dashboard
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    # Students
    path("students/", include("students.urls", namespace="students")),
    # Academics
    path("academics/", include("academics.urls", namespace="academics")),
    # Attendance
    path("attendance/", include("attendance.urls", namespace="attendance")),
    # Examinations
    path(
        "examinations/", include("examinations.urls", namespace="examinations")
    ),
    # Fees
    path("fees/", include("fees.urls", namespace="fees")),
    # Library
    path("library/", include("library.urls", namespace="library")),
    # Transport
    path("transport/", include("transport.urls", namespace="transport")),
    # Communications
    path(
        "communications/",
        include("communications.urls", namespace="communications"),
    ),
    # Reports
    path("reports/", include("reports.urls", namespace="reports")),
    # Home
    path("", include("dashboard.urls", namespace="home")),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
