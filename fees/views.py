from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from roles.decorators import permission_required
from roles.permissions import is_module_active
from students.models import AcademicYear, ClassLevel

from .forms import (
    AdminPaymentLookupForm,
    FeeInvoiceForm,
    FeePaymentForm,
    FeeStructureForm,
    FeeTypeForm,
)
from .models import FeeInvoice, FeePayment, FeeStructure, FeeType
from .services import (
    ensure_current_month_fee_invoices,
    generate_payment_reference,
    record_invoice_payment,
)


def _filter_invoices_for_user(queryset, user):
    """Restrict fee visibility for student and parent users."""
    if user.role == "student" and hasattr(user, "student_profile"):
        return queryset.filter(student=user.student_profile)

    if user.role == "parent" and hasattr(user, "parent_profile"):
        return queryset.filter(student__parents=user.parent_profile).distinct()

    return queryset


def _ensure_fee_settings_admin(request):
    """Restrict fee configuration screens to admins and superusers."""
    if not is_module_active("fees"):
        messages.error(request, "The fees module is currently inactive.")
        return HttpResponseForbidden("Permission denied.")

    if (
        request.user.is_superuser
        or request.user.role == "admin"
        or request.user.has_permission("fees", "manage_fee")
    ):
        return None

    messages.error(
        request,
        "Only administrators can manage fee settings.",
    )
    return HttpResponseForbidden("Permission denied.")


def _ensure_fee_portal_access(request):
    """Allow fee access for admins, parents, and users with fee view permission."""
    if not is_module_active("fees"):
        messages.error(request, "The fees module is currently inactive.")
        return HttpResponseForbidden("Permission denied.")

    user = request.user
    if (
        user.is_superuser
        or user.role in {"admin", "parent"}
        or user.has_permission("fees", "view")
    ):
        return None

    messages.error(request, "You don't have permission to view fees.")
    return HttpResponseForbidden("Permission denied.")


def _ensure_fee_action_access(request, permission_codename, message):
    """Allow admins and permitted users to perform fee actions."""
    if not is_module_active("fees"):
        messages.error(request, "The fees module is currently inactive.")
        return HttpResponseForbidden("Permission denied.")

    user = request.user
    if (
        user.is_superuser
        or user.role == "admin"
        or user.has_permission("fees", "manage_fee")
        or user.has_permission("fees", permission_codename)
    ):
        return None

    messages.error(request, message)
    return HttpResponseForbidden("Permission denied.")


@login_required
def fee_list(request):
    """Show fee invoices, balances, and recent payments."""
    denied_response = _ensure_fee_portal_access(request)
    if denied_response:
        return denied_response

    current_academic_year = AcademicYear.objects.filter(is_current=True).first()
    today = timezone.localdate()
    is_parent_view = request.user.role == "parent"

    if current_academic_year:
        ensure_current_month_fee_invoices(current_academic_year, today)

    invoices = (
        FeeInvoice.objects.select_related(
            "student__user",
            "student__class_level",
            "student__section",
            "fee_structure__fee_type",
            "academic_year",
        )
        .prefetch_related("payments")
        .order_by("-due_date", "-created_at")
    )
    invoices = _filter_invoices_for_user(invoices, request.user)

    selected_year = request.GET.get("year")
    selected_class = request.GET.get("class")
    selected_status = request.GET.get("status")
    search = request.GET.get("q", "").strip()

    if selected_year:
        invoices = invoices.filter(academic_year_id=selected_year)
    elif current_academic_year and not is_parent_view:
        invoices = invoices.filter(academic_year=current_academic_year)

    if selected_class and not is_parent_view:
        invoices = invoices.filter(student__class_level_id=selected_class)

    if selected_status and not is_parent_view:
        invoices = invoices.filter(status=selected_status)

    if search and not is_parent_view:
        invoices = invoices.filter(
            Q(student__user__first_name__icontains=search)
            | Q(student__user__last_name__icontains=search)
            | Q(student__admission_no__icontains=search)
            | Q(fee_structure__fee_type__name__icontains=search)
        )

    invoice_totals = invoices.aggregate(
        total_billed=Sum("total_amount"),
        total_paid=Sum("paid_amount"),
        total_due=Sum("due_amount"),
        overdue_count=Count(
            "id", filter=Q(due_date__lt=today, due_amount__gt=0)
        ),
        invoice_count=Count("id"),
    )
    total_billed = invoice_totals["total_billed"] or 0
    total_paid = invoice_totals["total_paid"] or 0
    total_due = invoice_totals["total_due"] or 0

    paginator = Paginator(invoices, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    recent_payments = (
        FeePayment.objects.select_related(
            "invoice__student__user",
            "invoice__fee_structure__fee_type",
        )
        .filter(invoice__in=invoices.values("pk"))
        .order_by("-payment_date", "-created_at")[:8]
    )

    context = {
        "current_academic_year": current_academic_year,
        "academic_years": AcademicYear.objects.filter(is_active=True),
        "classes": ClassLevel.objects.filter(is_active=True).order_by(
            "numeric_name"
        ),
        "invoices": page_obj.object_list,
        "recent_payments": recent_payments,
        "total_billed": total_billed,
        "total_paid": total_paid,
        "total_due": total_due,
        "overdue_count": invoice_totals["overdue_count"] or 0,
        "invoice_count": invoice_totals["invoice_count"] or 0,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "today": today,
        "selected_year": selected_year,
        "selected_class": selected_class,
        "selected_status": selected_status,
        "search_query": search,
        "is_parent_view": is_parent_view,
    }
    return render(request, "fees/list.html", context)


@login_required
def create_invoice(request):
    """Create a new fee invoice."""
    denied_response = _ensure_fee_action_access(
        request,
        "add",
        "You don't have permission to create fee invoices.",
    )
    if denied_response:
        return denied_response

    form = FeeInvoiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee invoice created successfully.")
        return redirect("fees:list")

    return render(
        request,
        "fees/invoice_form.html",
        {"form": form, "object": None},
    )


@login_required
def edit_invoice(request, pk):
    """Update an existing fee invoice."""
    denied_response = _ensure_fee_action_access(
        request,
        "edit",
        "You don't have permission to update fee invoices.",
    )
    if denied_response:
        return denied_response

    invoice = get_object_or_404(
        FeeInvoice.objects.select_related(
            "student__user", "student__class_level", "fee_structure__fee_type"
        ),
        pk=pk,
    )
    form = FeeInvoiceForm(request.POST or None, instance=invoice)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee invoice updated successfully.")
        return redirect("fees:list")

    return render(
        request,
        "fees/invoice_form.html",
        {"form": form, "object": invoice},
    )


@login_required
def delete_invoice(request, pk):
    """Delete a fee invoice."""
    denied_response = _ensure_fee_action_access(
        request,
        "delete",
        "You don't have permission to delete fee invoices.",
    )
    if denied_response:
        return denied_response

    invoice = get_object_or_404(
        FeeInvoice.objects.select_related("student__user", "fee_structure__fee_type"),
        pk=pk,
    )
    if request.method == "POST":
        invoice.delete()
        messages.success(request, "Fee invoice deleted successfully.")
        return redirect("fees:list")

    return render(
        request,
        "fees/confirm_delete.html",
        {
            "object": invoice,
            "title": "Delete Fee Invoice",
            "cancel_url": "fees:list",
        },
    )


@login_required
def payment(request):
    """Render payment page and allow users to pay visible invoices."""
    denied_response = _ensure_fee_portal_access(request)
    if denied_response:
        return denied_response

    if request.user.role != "parent":
        denied_response = _ensure_fee_action_access(
            request,
            "collect",
            "You don't have permission to complete fee payments.",
        )
        if denied_response:
            return denied_response

    invoice_queryset = FeeInvoice.objects.select_related(
        "student__user",
        "student__class_level",
        "student__section",
        "fee_structure__fee_type",
        "academic_year",
    )
    invoice_queryset = _filter_invoices_for_user(
        invoice_queryset, request.user
    )

    invoice_id = request.GET.get("invoice") or request.POST.get("invoice_id")
    selected_invoice = None
    if invoice_id:
        selected_invoice = get_object_or_404(invoice_queryset, pk=invoice_id)

    payment_form = FeePaymentForm(request.POST or None)
    admin_lookup_form = None
    matching_invoices = FeeInvoice.objects.none()

    # if request.user.role != "parent":
    #     admin_lookup_form = AdminPaymentLookupForm(request.GET or None)
    #     if (
    #         request.method == "GET"
    #         and selected_invoice is None
    #         and admin_lookup_form.is_bound
    #         and admin_lookup_form.is_valid()
    #     ):
    #         class_level = admin_lookup_form.cleaned_data["class_level"]
    #         matching_invoices = (
    #             invoice_queryset.filter(
    #                 student=admin_lookup_form.cleaned_data["student"],
    #                 fee_structure=admin_lookup_form.cleaned_data[
    #                     "fee_structure"
    #                 ],
    #                 academic_year=admin_lookup_form.cleaned_data[
    #                     "academic_year"
    #                 ],
    #                 due_amount__gt=0,
    #             )
    #             .order_by("due_date", "created_at")
    #         )
    #         if class_level:
    #             matching_invoices = matching_invoices.filter(
    #                 student__class_level=class_level,
    #                 fee_structure__class_level=class_level,
    #             )

    if request.method == "POST":
        if selected_invoice is None:
            messages.error(request, "Please choose an invoice to pay.")
            return redirect("fees:list")

        if selected_invoice.due_amount <= 0:
            messages.info(request, "This invoice is already fully paid.")
            return redirect(f"{request.path}?invoice={selected_invoice.pk}")

        if payment_form.is_valid():
            payment_mode = payment_form.cleaned_data["payment_mode"]
            remarks = payment_form.cleaned_data["remarks"].strip()
            default_remarks = (
                "Paid from parent fee portal."
                if request.user.role == "parent"
                else "Paid from fee desk."
            )
            normalized_remarks = remarks or default_remarks

            if payment_mode == "cash":
                payment = record_invoice_payment(
                    selected_invoice,
                    payment_mode=payment_mode,
                    remarks=normalized_remarks,
                )
                messages.success(
                    request,
                    f"Cash payment of ${payment.amount} recorded successfully.",
                )
                return redirect("fees:list")

            transaction_id = generate_payment_reference("TXN")
            context = {
                "selected_invoice": selected_invoice,
                "payment_form": payment_form,
                "gateway_mode": payment_mode,
                "gateway_transaction_id": transaction_id,
                "gateway_remarks": normalized_remarks,
            }
            return render(request, "fees/payment_gateway.html", context)

    context = {
        "selected_invoice": selected_invoice,
        "payment_form": payment_form,
        "admin_lookup_form": admin_lookup_form,
        "matching_invoices": matching_invoices,
    }
    return render(request, "fees/payment.html", context)


@login_required
def payment_gateway(request):
    """Gateway step for online-style payments before final capture."""
    denied_response = _ensure_fee_portal_access(request)
    if denied_response:
        return denied_response

    if request.user.role != "parent":
        denied_response = _ensure_fee_action_access(
            request,
            "collect",
            "You don't have permission to complete fee payments.",
        )
        if denied_response:
            return denied_response

    invoice_queryset = FeeInvoice.objects.select_related(
        "student__user",
        "student__class_level",
        "student__section",
        "fee_structure__fee_type",
        "academic_year",
    )
    invoice_queryset = _filter_invoices_for_user(
        invoice_queryset, request.user
    )

    selected_invoice = get_object_or_404(
        invoice_queryset, pk=request.POST.get("invoice_id")
    )

    if selected_invoice.due_amount <= 0:
        messages.info(request, "This invoice is already fully paid.")
        return redirect("fees:list")

    payment_mode = request.POST.get("payment_mode", "").strip()
    if payment_mode not in {"online", "card", "bank_transfer", "cheque"}:
        messages.error(request, "Please choose a valid gateway payment mode.")
        return redirect(f"{reverse('fees:payment')}?invoice={selected_invoice.pk}")

    payment = record_invoice_payment(
        selected_invoice,
        payment_mode=payment_mode,
        remarks=request.POST.get("remarks", "").strip() or "Gateway payment",
        transaction_id=request.POST.get("transaction_id", "").strip()
        or generate_payment_reference("TXN"),
    )
    messages.success(
        request,
        f"{payment.get_payment_mode_display()} payment of ${payment.amount} completed successfully.",
    )
    return redirect("fees:list")


@login_required
def fee_type_list(request):
    """List fee types for settings management."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    fee_types = FeeType.objects.order_by("name")
    context = {
        "fee_types": fee_types,
    }
    return render(request, "fees/fee_type_list.html", context)


@login_required
def fee_type_create(request):
    """Create a fee type."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    form = FeeTypeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee type created successfully.")
        return redirect("fees:fee_type_list")

    return render(
        request,
        "fees/fee_type_form.html",
        {"form": form, "object": None},
    )


@login_required
def fee_type_edit(request, pk):
    """Update a fee type."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    fee_type = get_object_or_404(FeeType, pk=pk)
    form = FeeTypeForm(request.POST or None, instance=fee_type)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee type updated successfully.")
        return redirect("fees:fee_type_list")

    return render(
        request,
        "fees/fee_type_form.html",
        {"form": form, "object": fee_type},
    )


@login_required
def fee_type_delete(request, pk):
    """Delete a fee type."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    fee_type = get_object_or_404(FeeType, pk=pk)
    if request.method == "POST":
        fee_type.delete()
        messages.success(request, "Fee type deleted successfully.")
        return redirect("fees:fee_type_list")

    return render(
        request,
        "fees/confirm_delete.html",
        {
            "object": fee_type,
            "title": "Delete Fee Type",
            "cancel_url": "fees:fee_type_list",
        },
    )


@login_required
def fee_structure_list(request):
    """List fee structures for settings management."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    fee_structures = (
        FeeStructure.objects.select_related(
            "class_level",
            "fee_type",
            "academic_year",
        ).order_by(
            "-academic_year__start_date",
            "class_level__numeric_name",
            "fee_type__name",
        )
    )

    context = {
        "fee_structures": fee_structures,
    }
    return render(request, "fees/fee_structure_list.html", context)


@login_required
def fee_structure_create(request):
    """Create a fee structure."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    form = FeeStructureForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee structure created successfully.")
        return redirect("fees:fee_structure_list")

    return render(
        request,
        "fees/fee_structure_form.html",
        {"form": form, "object": None},
    )


@login_required
def fee_structure_edit(request, pk):
    """Update a fee structure."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    fee_structure = get_object_or_404(FeeStructure, pk=pk)
    form = FeeStructureForm(request.POST or None, instance=fee_structure)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee structure updated successfully.")
        return redirect("fees:fee_structure_list")

    return render(
        request,
        "fees/fee_structure_form.html",
        {"form": form, "object": fee_structure},
    )


@login_required
def fee_structure_delete(request, pk):
    """Delete a fee structure."""
    denied_response = _ensure_fee_settings_admin(request)
    if denied_response:
        return denied_response

    fee_structure = get_object_or_404(FeeStructure, pk=pk)
    if request.method == "POST":
        fee_structure.delete()
        messages.success(request, "Fee structure deleted successfully.")
        return redirect("fees:fee_structure_list")

    return render(
        request,
        "fees/confirm_delete.html",
        {
            "object": fee_structure,
            "title": "Delete Fee Structure",
            "cancel_url": "fees:fee_structure_list",
        },
    )
