from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.models import User
from students.models import AcademicYear, ClassLevel, Student

from .models import RouteStop, TransportAssignment, TransportRoute, Vehicle


@patch("transport.views.is_module_active", return_value=True)
@patch("accounts.models.User.has_permission", return_value=True)
class TransportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="transport1",
            password="testpass123",
            role="teacher",
        )
        self.academic_year = AcademicYear.objects.create(
            name="2026-2027",
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 5",
            numeric_name=5,
        )
        student_user = User.objects.create_user(
            username="student_transport",
            password="testpass123",
            role="student",
        )
        self.student = Student.objects.create(
            user=student_user,
            admission_no="ADM-5001",
            admission_date="2026-01-10",
            date_of_birth="2013-02-01",
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_no="BUS-101",
            vehicle_type="bus",
            model="Ashok Leyland",
            capacity=40,
            driver_name="Rahim",
            driver_phone="0123456789",
        )
        self.route = TransportRoute.objects.create(
            route_no="R-01",
            name="North Route",
            vehicle=self.vehicle,
            fare=1500,
        )
        self.stop = RouteStop.objects.create(
            route=self.route,
            name="Main Gate",
            arrival_time="07:30",
            departure_time="07:35",
            stop_order=1,
        )
        TransportAssignment.objects.create(
            student=self.student,
            route=self.route,
            pickup_point=self.stop,
            academic_year=self.academic_year,
            start_date="2026-01-10",
        )

    def test_routes_page_renders_transport_data(
        self, mocked_has_permission, mocked_module_active
    ):
        self.client.force_login(self.user)

        response = self.client.get(reverse("transport:routes"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transport")
        self.assertContains(response, "North Route")
        self.assertContains(response, "BUS-101")

    def test_routes_page_filters_by_search(
        self, mocked_has_permission, mocked_module_active
    ):
        self.client.force_login(self.user)

        response = self.client.get(reverse("transport:routes"), {"q": "north"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "North Route")
        self.assertNotContains(response, "No routes found")
