from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from roles.permissions import is_module_active

from .models import Book, BookIssue


def _ensure_library_access(request):
    """Allow access to the library dashboard for authorized users."""
    if not is_module_active("library"):
        messages.error(request, "The library module is currently inactive.")
        return HttpResponseForbidden("Permission denied.")

    user = request.user
    if (
        user.is_superuser
        or user.role == "admin"
        or user.has_permission("library", "view")
        or user.has_permission("library", "issue")
    ):
        return None

    messages.error(request, "You don't have permission to view library records.")
    return HttpResponseForbidden("Permission denied.")


@login_required
def library_index(request):
    """Send the library root to the main books page."""
    denied_response = _ensure_library_access(request)
    if denied_response:
        return denied_response

    return redirect("library:books")


@login_required
def book_list(request):
    """Show the library overview and searchable book catalog."""
    denied_response = _ensure_library_access(request)
    if denied_response:
        return denied_response

    search_query = request.GET.get("q", "").strip()
    availability_filter = request.GET.get("availability", "").strip()

    books = Book.objects.select_related("category").filter(is_active=True)
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query)
            | Q(author__icontains=search_query)
            | Q(isbn__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    if availability_filter == "available":
        books = books.filter(available__gt=0)
    elif availability_filter == "unavailable":
        books = books.filter(available__lte=0)

    books = books.order_by("title", "author")
    total_filtered_books = books.count()
    paginator = Paginator(books, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    recent_issues = (
        BookIssue.objects.select_related(
            "student__user",
            "student__class_level",
            "book",
        )
        .order_by("-issue_date")[:6]
    )

    stats = Book.objects.filter(is_active=True).aggregate(
        total_titles=Count("id"),
        total_copies=Sum("quantity"),
        available_copies=Sum("available"),
    )
    total_titles = stats["total_titles"] or 0
    total_copies = stats["total_copies"] or 0
    available_copies = stats["available_copies"] or 0
    issued_copies = max(total_copies - available_copies, 0)
    today = timezone.localdate()
    overdue_count = BookIssue.objects.filter(
        status="issued",
        due_date__lt=today,
    ).count()

    context = {
        "books": page_obj.object_list,
        "total_filtered_books": total_filtered_books,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "recent_issues": recent_issues,
        "search_query": search_query,
        "selected_availability": availability_filter,
        "total_titles": total_titles,
        "total_copies": total_copies,
        "available_copies": available_copies,
        "issued_copies": issued_copies,
        "overdue_count": overdue_count,
        "today": today,
    }
    return render(request, "library/books.html", context)
