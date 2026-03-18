import calendar
from datetime import date
import uuid

from django.utils import timezone

from .models import FeeInvoice, FeePayment, FeeStructure


def _resolve_invoice_due_date(admission_date, configured_due_date):
    """Map the configured fee day onto the student's admission month."""
    if not configured_due_date:
        return admission_date

    last_day = calendar.monthrange(
        admission_date.year, admission_date.month
    )[1]
    target_day = min(configured_due_date.day, last_day)
    resolved_date = date(
        admission_date.year, admission_date.month, target_day
    )
    return max(resolved_date, admission_date)


def _create_invoice_if_missing(student, fee_structure, due_date):
    """Create an invoice once for the same student, structure, and due date."""
    existing_invoice = FeeInvoice.objects.filter(
        student=student,
        fee_structure=fee_structure,
        academic_year=student.academic_year,
        due_date=due_date,
    ).exists()
    if existing_invoice:
        return False

    FeeInvoice.objects.create(
        student=student,
        fee_structure=fee_structure,
        academic_year=student.academic_year,
        total_amount=fee_structure.amount,
        paid_amount=0,
        due_amount=fee_structure.amount,
        due_date=due_date,
    )
    return True


def _resolve_monthly_due_date(target_date, admission_date, configured_due_date):
    """Build the due date for a recurring monthly invoice."""
    last_day = calendar.monthrange(target_date.year, target_date.month)[1]
    target_day = 1
    if configured_due_date:
        target_day = min(configured_due_date.day, last_day)

    resolved_date = date(target_date.year, target_date.month, target_day)

    if (
        admission_date.year == target_date.year
        and admission_date.month == target_date.month
    ):
        return max(resolved_date, admission_date)

    return resolved_date


def create_admission_fee_invoices(student):
    """
    Create first-time invoices when a student is admitted.

    Rules:
    - `monthly` fee structures create invoices for the admission month.
    - `one_time` fee structures create admission-time invoices.
    """
    fee_structures = FeeStructure.objects.select_related("fee_type").filter(
        class_level=student.class_level,
        academic_year=student.academic_year,
        is_active=True,
        fee_type__is_active=True,
        fee_type__category__in=["monthly", "one_time"],
    )

    created_counts = {
        "monthly": 0,
        "one_time": 0,
        "total": 0,
    }

    for fee_structure in fee_structures:
        fee_category = fee_structure.fee_type.category
        due_date = _resolve_invoice_due_date(
            student.admission_date, fee_structure.due_date
        )

        if _create_invoice_if_missing(student, fee_structure, due_date):
            created_counts[fee_category] += 1
            created_counts["total"] += 1

    return created_counts


def ensure_current_month_fee_invoices(academic_year, target_date):
    """
    Create missing monthly invoices for the given month.

    This keeps the fee desk from silently missing the current month's dues
    when a monthly invoice was never generated for a student.
    """
    if academic_year is None:
        return 0

    from students.models import Student

    eligible_students = Student.objects.select_related(
        "class_level", "academic_year"
    ).filter(
        academic_year=academic_year,
        status="studying",
        is_active=True,
        admission_date__lte=target_date,
    )

    created_count = 0

    for student in eligible_students:
        fee_structures = FeeStructure.objects.select_related("fee_type").filter(
            class_level=student.class_level,
            academic_year=student.academic_year,
            is_active=True,
            fee_type__is_active=True,
            fee_type__category="monthly",
        )

        for fee_structure in fee_structures:
            due_date = _resolve_monthly_due_date(
                target_date,
                student.admission_date,
                fee_structure.due_date,
            )
            if _create_invoice_if_missing(student, fee_structure, due_date):
                created_count += 1

    return created_count


def generate_payment_reference(prefix):
    """Generate a short unique payment reference."""
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


def record_invoice_payment(
    invoice,
    payment_mode,
    remarks="",
    payment_date=None,
    transaction_id="",
):
    """Persist a payment and update the invoice balance."""
    payment_amount = invoice.due_amount
    payment = FeePayment.objects.create(
        invoice=invoice,
        amount=payment_amount,
        payment_date=payment_date or timezone.localdate(),
        payment_mode=payment_mode,
        transaction_id=transaction_id,
        receipt_no=generate_payment_reference("RCT"),
        remarks=remarks,
    )
    invoice.paid_amount += payment_amount
    invoice.save()
    return payment
