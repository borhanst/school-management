from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from fees.models import FeeInvoice, FeePayment, FeeStructure, FeeType
from roles.models import Module, PermissionType, Role, RolePermission, UserRole
from students.models import AcademicYear, ClassLevel, Student


class FeeSettingsCrudTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="fee_admin",
            password="pass12345",
            role="admin",
        )
        self.teacher_user = User.objects.create_user(
            username="fee_teacher",
            password="pass12345",
            role="teacher",
        )
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 6",
            numeric_name=6,
        )
        self.fee_type = FeeType.objects.create(
            name="Tuition Fee",
            category="monthly",
        )

    def test_admin_can_create_fee_type(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("fees:fee_type_create"),
            {
                "name": "Transport Fee",
                "category": "monthly",
                "description": "Monthly transport charge",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("fees:fee_type_list"))
        self.assertTrue(FeeType.objects.filter(name="Transport Fee").exists())

    def test_non_admin_cannot_open_fee_type_settings(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse("fees:fee_type_list"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_fee_structure(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("fees:fee_structure_create"),
            {
                "class_level": self.class_level.id,
                "fee_type": self.fee_type.id,
                "academic_year": self.academic_year.id,
                "amount": "5000.00",
                "due_date": "2025-01-10",
                "late_fee": "50.00",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("fees:fee_structure_list"))
        self.assertTrue(
            FeeStructure.objects.filter(
                class_level=self.class_level,
                fee_type=self.fee_type,
                academic_year=self.academic_year,
            ).exists()
        )

    def test_admin_can_create_invoice(self):
        student_user = User.objects.create_user(
            username="invoice_student",
            password="pass12345",
            role="student",
            first_name="Hasan",
        )
        student = Student.objects.create(
            user=student_user,
            admission_no="ADM2025009",
            admission_date=date(2025, 1, 3),
            date_of_birth=date(2014, 1, 1),
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        fee_structure = FeeStructure.objects.create(
            class_level=self.class_level,
            fee_type=self.fee_type,
            academic_year=self.academic_year,
            amount=Decimal("5000.00"),
            due_date=date(2025, 1, 10),
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("fees:create_invoice"),
            {
                "student": student.id,
                "fee_structure": fee_structure.id,
                "academic_year": self.academic_year.id,
                "total_amount": "5000.00",
                "paid_amount": "0.00",
                "due_date": "2025-01-10",
                "status": "pending",
            },
        )

        self.assertRedirects(response, reverse("fees:list"))
        self.assertTrue(FeeInvoice.objects.filter(student=student).exists())

    def test_settings_page_shows_fee_management_links(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("accounts:settings"))

        self.assertContains(response, reverse("fees:fee_type_list"))
        self.assertContains(response, reverse("fees:fee_structure_list"))

    def test_user_with_manage_fee_permission_can_open_fee_settings(self):
        manager_user = User.objects.create_user(
            username="fee_manager",
            password="pass12345",
            role="teacher",
        )
        fees_module = Module.objects.create(
            name="Fees",
            slug="fees",
            description="Fee management",
            order=5,
        )
        manage_fee_permission = PermissionType.objects.create(
            module=fees_module,
            name="Manage Fee",
            codename="manage_fee",
            order=99,
        )
        role_permission = RolePermission.objects.create(
            module=fees_module,
            permission_type=manage_fee_permission,
        )
        manager_role = Role.objects.create(
            name="Fee Manager",
            description="Can manage fee operations",
            priority=40,
        )
        manager_role.permissions.add(role_permission)
        UserRole.objects.create(user=manager_user, role=manager_role)

        self.client.force_login(manager_user)

        response = self.client.get(reverse("fees:fee_type_list"))

        self.assertEqual(response.status_code, 200)


class ParentFeeVisibilityTests(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 7",
            numeric_name=7,
        )
        self.parent_user = User.objects.create_user(
            username="parent_user",
            password="pass12345",
            role="parent",
        )
        self.student_user = User.objects.create_user(
            username="student_user",
            password="pass12345",
            role="student",
            first_name="Rahim",
        )
        self.student = Student.objects.create(
            user=self.student_user,
            admission_no="ADM2025001",
            admission_date=date(2025, 1, 5),
            date_of_birth=date(2015, 5, 1),
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.parent_user.parent_profile.children.add(self.student)
        self.fee_type = FeeType.objects.create(
            name="Admission Fee",
            category="one_time",
        )
        self.fee_structure = FeeStructure.objects.create(
            class_level=self.class_level,
            fee_type=self.fee_type,
            academic_year=self.academic_year,
            amount=Decimal("2500.00"),
            due_date=date(2025, 1, 10),
        )
        self.invoice = FeeInvoice.objects.create(
            student=self.student,
            fee_structure=self.fee_structure,
            academic_year=self.academic_year,
            total_amount=Decimal("2500.00"),
            paid_amount=Decimal("0.00"),
            due_date=date(2025, 1, 10),
        )

    def test_parent_can_see_linked_child_due_invoice(self):
        self.client.force_login(self.parent_user)

        response = self.client.get(reverse("fees:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Child Fee Invoices")
        self.assertContains(response, "Rahim")
        self.assertContains(response, "Admission Fee")

    def test_parent_can_see_paid_invoice_history(self):
        self.invoice.paid_amount = Decimal("2500.00")
        self.invoice.save()
        self.client.force_login(self.parent_user)

        response = self.client.get(reverse("fees:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paid")
        self.assertContains(response, "Admission Fee")

    def test_cash_payment_records_immediately(self):
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse("fees:payment"),
            {
                "invoice_id": self.invoice.id,
                "payment_mode": "cash",
                "remarks": "Collected at desk",
            },
        )

        self.assertRedirects(response, reverse("fees:list"))
        self.invoice.refresh_from_db()
        payment = FeePayment.objects.get(invoice=self.invoice)
        self.assertEqual(payment.payment_mode, "cash")
        self.assertEqual(payment.remarks, "Collected at desk")
        self.assertEqual(self.invoice.status, "paid")

    def test_online_payment_goes_to_gateway_step(self):
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse("fees:payment"),
            {
                "invoice_id": self.invoice.id,
                "payment_mode": "online",
                "remarks": "Gateway payment",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gateway Step")
        self.assertContains(response, "Complete Payment")
        self.assertFalse(FeePayment.objects.filter(invoice=self.invoice).exists())


class AdminInvoiceManagementTests(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 9",
            numeric_name=9,
        )
        self.admin_user = User.objects.create_user(
            username="fees_admin_user",
            password="pass12345",
            role="admin",
        )
        self.student_user = User.objects.create_user(
            username="fees_student_user",
            password="pass12345",
            role="student",
            first_name="Mina",
        )
        self.student = Student.objects.create(
            user=self.student_user,
            admission_no="ADM2025010",
            admission_date=date(2025, 1, 2),
            date_of_birth=date(2013, 2, 2),
            gender="female",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.fee_type = FeeType.objects.create(
            name="Exam Fee",
            category="one_time",
        )
        self.fee_structure = FeeStructure.objects.create(
            class_level=self.class_level,
            fee_type=self.fee_type,
            academic_year=self.academic_year,
            amount=Decimal("1200.00"),
            due_date=date(2025, 1, 15),
        )
        self.invoice = FeeInvoice.objects.create(
            student=self.student,
            fee_structure=self.fee_structure,
            academic_year=self.academic_year,
            total_amount=Decimal("1200.00"),
            paid_amount=Decimal("0.00"),
            due_date=date(2025, 1, 15),
        )

    def test_admin_can_update_invoice(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("fees:edit_invoice", args=[self.invoice.id]),
            {
                "student": self.student.id,
                "fee_structure": self.fee_structure.id,
                "academic_year": self.academic_year.id,
                "total_amount": "1500.00",
                "paid_amount": "0.00",
                "due_date": "2025-01-20",
                "status": "pending",
            },
        )

        self.assertRedirects(response, reverse("fees:list"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal("1500.00"))

    def test_admin_can_delete_invoice(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("fees:delete_invoice", args=[self.invoice.id])
        )

        self.assertRedirects(response, reverse("fees:list"))
        self.assertFalse(FeeInvoice.objects.filter(id=self.invoice.id).exists())

    def test_admin_can_complete_payment(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("fees:payment"),
            {
                "invoice_id": self.invoice.id,
                "payment_mode": "cash",
                "remarks": "Admin desk collection",
            },
        )

        self.assertRedirects(response, reverse("fees:list"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "paid")
        self.assertTrue(FeePayment.objects.filter(invoice=self.invoice).exists())

    def test_admin_payment_page_shows_searchable_lookup_form(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("fees:payment"),
            {
                "student": self.student.id,
                "fee_structure": self.fee_structure.id,
                "academic_year": self.academic_year.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find Invoice to Collect Payment")
        self.assertContains(response, 'class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-opacity-20 django-select2"')
        self.assertContains(response, "Mina - ADM2025010 - Class 9")
        self.assertContains(response, "Select Invoice")


class MissingMonthlyInvoiceTests(TestCase):
    def setUp(self):
        today = date.today()
        self.academic_year = AcademicYear.objects.create(
            name=f"{today.year}-{today.year + 1}",
            start_date=date(today.year, 1, 1),
            end_date=date(today.year, 12, 31),
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            name="Class 8",
            numeric_name=8,
        )
        self.admin_user = User.objects.create_user(
            username="invoice_admin",
            password="pass12345",
            role="admin",
        )
        self.student_user = User.objects.create_user(
            username="missing_invoice_student",
            password="pass12345",
            role="student",
            first_name="Karim",
        )
        self.student = Student.objects.create(
            user=self.student_user,
            admission_no="ADM2025002",
            admission_date=date(today.year, 1, 5),
            date_of_birth=date(today.year - 10, 5, 1),
            gender="male",
            class_level=self.class_level,
            academic_year=self.academic_year,
        )
        self.monthly_fee_type = FeeType.objects.create(
            name="Monthly Tuition",
            category="monthly",
        )
        self.monthly_structure = FeeStructure.objects.create(
            class_level=self.class_level,
            fee_type=self.monthly_fee_type,
            academic_year=self.academic_year,
            amount=Decimal("3000.00"),
            due_date=date(today.year, today.month, 5),
        )

    def test_fee_list_creates_missing_current_month_invoice(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("fees:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Karim")
        self.assertTrue(
            FeeInvoice.objects.filter(
                student=self.student,
                fee_structure=self.monthly_structure,
                due_date__year=date.today().year,
                due_date__month=date.today().month,
            ).exists()
        )
