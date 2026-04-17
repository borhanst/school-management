from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from roles.permissions import is_module_active

from .models import Notice, NoticeView


def _ensure_notice_access(request):
    """Allow notice access for admins and users with communications access."""
    if not is_module_active("communications"):
        messages.error(request, "The communications module is currently inactive.")
        return HttpResponseForbidden("Permission denied.")

    user = request.user
    if (
        user.is_superuser
        or user.role == "admin"
        or user.has_permission("communications", "view")
        or user.has_permission("communications", "publish")
    ):
        return None

    messages.error(request, "You don't have permission to view notices.")
    return HttpResponseForbidden("Permission denied.")


def _get_child_class_ids(user):
    if user.role != "parent" or not hasattr(user, "parent_profile"):
        return set()

    return set(
        user.parent_profile.children.values_list("class_level_id", flat=True)
    )


def _notice_visible_to_user(notice, user, child_class_ids=None):
    """Evaluate role/class targeting in Python for portability."""
    if user.is_superuser or user.role == "admin":
        return True

    roles = notice.for_roles or []
    if roles and user.role not in roles:
        return False

    class_ids = {class_level.id for class_level in notice.for_classes.all()}
    if not class_ids:
        return True

    if user.role == "student" and hasattr(user, "student_profile"):
        return user.student_profile.class_level_id in class_ids

    if user.role == "parent":
        return bool((child_class_ids or set()) & class_ids)

    return True


@login_required
def notice_list(request):
    """Show current notices for the signed-in user."""
    denied_response = _ensure_notice_access(request)
    if denied_response:
        return denied_response

    now = timezone.now()
    type_filter = request.GET.get("type", "").strip()
    search_query = request.GET.get("q", "").strip()

    notices = (
        Notice.objects.filter(
            is_active=True,
            publish_date__lte=now,
        )
        .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=now))
        .select_related("posted_by")
        .prefetch_related(
            Prefetch("for_classes"),
        )
        .annotate(view_count=Count("views"))
        .order_by("-is_pinned", "-publish_date")
    )

    visible_notices = [
        notice
        for notice in notices
        if _notice_visible_to_user(
            notice,
            request.user,
            child_class_ids=_get_child_class_ids(request.user),
        )
    ]

    if type_filter:
        visible_notices = [
            notice
            for notice in visible_notices
            if notice.notice_type == type_filter
        ]

    if search_query:
        normalized_query = search_query.lower()
        visible_notices = [
            notice
            for notice in visible_notices
            if normalized_query in notice.title.lower()
            or normalized_query in notice.content.lower()
        ]

    paginator = Paginator(visible_notices, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_notices = list(page_obj.object_list)

    NoticeView.objects.bulk_create(
        [
            NoticeView(notice=notice, user=request.user)
            for notice in page_notices
        ],
        ignore_conflicts=True,
    )

    context = {
        "notices": page_notices,
        "notice_count": len(visible_notices),
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "selected_type": type_filter,
        "search_query": search_query,
        "notice_types": Notice.NOTICE_TYPE_CHOICES,
        "pinned_count": sum(1 for notice in visible_notices if notice.is_pinned),
        "fee_notice_count": sum(
            1 for notice in visible_notices if notice.notice_type == "fee"
        ),
        "attachment_count": sum(
            1 for notice in visible_notices if notice.attachment
        ),
        "now": now,
    }
    return render(request, "communications/notices.html", context)
