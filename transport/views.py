from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from roles.permissions import is_module_active

from .models import TransportAssignment, TransportRoute, Vehicle


def _ensure_transport_access(request):
    """Allow access to transport screens for authorized users."""
    if not is_module_active("transport"):
        messages.error(request, "The transport module is currently inactive.")
        return HttpResponseForbidden("Permission denied.")

    user = request.user
    if (
        user.is_superuser
        or user.role == "admin"
        or user.has_permission("transport", "view")
        or user.has_permission("transport", "track")
    ):
        return None

    messages.error(request, "You don't have permission to view transport data.")
    return HttpResponseForbidden("Permission denied.")


@login_required
def transport_index(request):
    """Redirect transport root to the route overview."""
    denied_response = _ensure_transport_access(request)
    if denied_response:
        return denied_response

    return redirect("transport:routes")


@login_required
def route_list(request):
    """Show transport routes, fleet status, and active assignments."""
    denied_response = _ensure_transport_access(request)
    if denied_response:
        return denied_response

    search_query = request.GET.get("q", "").strip()
    vehicle_filter = request.GET.get("vehicle", "").strip()

    routes = (
        TransportRoute.objects.select_related("vehicle")
        .prefetch_related("stops")
        .annotate(
            stop_count=Count("stops", distinct=True),
            student_count=Count(
                "assignments",
                filter=Q(assignments__is_active=True),
                distinct=True,
            ),
        )
        .filter(is_active=True)
    )

    if search_query:
        routes = routes.filter(
            Q(route_no__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(vehicle__vehicle_no__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    if vehicle_filter == "assigned":
        routes = routes.filter(vehicle__isnull=False)
    elif vehicle_filter == "unassigned":
        routes = routes.filter(vehicle__isnull=True)

    routes = routes.order_by("route_no", "name")

    vehicles = Vehicle.objects.filter(is_active=True).order_by("vehicle_no")
    recent_assignments = (
        TransportAssignment.objects.select_related(
            "student__user",
            "student__class_level",
            "route",
            "pickup_point",
            "academic_year",
        )
        .filter(is_active=True)
        .order_by("-start_date")[:6]
    )

    vehicle_stats = Vehicle.objects.filter(is_active=True).aggregate(
        total_vehicles=Count("id"),
        total_capacity=Sum("capacity"),
    )
    total_vehicles = vehicle_stats["total_vehicles"] or 0
    total_capacity = vehicle_stats["total_capacity"] or 0
    active_assignments = TransportAssignment.objects.filter(
        is_active=True
    ).count()
    routes_with_vehicle = TransportRoute.objects.filter(
        is_active=True,
        vehicle__isnull=False,
    ).count()
    today = timezone.localdate()
    upcoming_expiry_count = Vehicle.objects.filter(
        is_active=True,
    ).filter(
        Q(insurance_expiry__isnull=False, insurance_expiry__lte=today + timedelta(days=30))
        | Q(permit_expiry__isnull=False, permit_expiry__lte=today + timedelta(days=30))
    ).count()

    context = {
        "routes": routes,
        "vehicles": vehicles,
        "recent_assignments": recent_assignments,
        "search_query": search_query,
        "selected_vehicle": vehicle_filter,
        "total_routes": routes.count(),
        "total_vehicles": total_vehicles,
        "total_capacity": total_capacity,
        "active_assignments": active_assignments,
        "routes_with_vehicle": routes_with_vehicle,
        "upcoming_expiry_count": upcoming_expiry_count,
        "today": today,
    }
    return render(request, "transport/routes.html", context)
