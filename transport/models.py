from django.db import models
from django.utils.translation import gettext_lazy as _


class Vehicle(models.Model):
    """Vehicle model."""

    VEHICLE_TYPE_CHOICES = [
        ("bus", "Bus"),
        ("van", "Van"),
        ("car", "Car"),
        ("other", "Other"),
    ]

    vehicle_no = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    model = models.CharField(max_length=50)
    capacity = models.IntegerField(default=50)
    driver_name = models.CharField(max_length=100)
    driver_phone = models.CharField(max_length=20)
    driver_license = models.CharField(max_length=50, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    permit_expiry = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(
        upload_to="transport/vehicles/", blank=True, null=True
    )

    class Meta:
        db_table = "transport_vehicle"
        verbose_name = _("vehicle")
        verbose_name_plural = _("vehicles")

    def __str__(self):
        return f"{self.vehicle_no} - {self.vehicle_type}"


class TransportRoute(models.Model):
    """Transport route model."""

    route_no = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routes",
    )
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "transport_route"
        verbose_name = _("transport route")
        verbose_name_plural = _("transport routes")

    def __str__(self):
        return f"{self.route_no} - {self.name}"


class RouteStop(models.Model):
    """Route stop model."""

    route = models.ForeignKey(
        TransportRoute, on_delete=models.CASCADE, related_name="stops"
    )
    name = models.CharField(max_length=100)
    arrival_time = models.TimeField()
    departure_time = models.TimeField()
    stop_order = models.IntegerField(default=0)
    address = models.TextField(blank=True)

    class Meta:
        db_table = "transport_route_stop"
        verbose_name = _("route stop")
        verbose_name_plural = _("route stops")
        ordering = ["stop_order"]

    def __str__(self):
        return f"{self.route} - {self.name}"


class TransportAssignment(models.Model):
    """Transport assignment model."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="transport_assignments",
    )
    route = models.ForeignKey(
        TransportRoute, on_delete=models.CASCADE, related_name="assignments"
    )
    pickup_point = models.ForeignKey(
        RouteStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pickup_students",
    )
    drop_point = models.ForeignKey(
        RouteStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drop_students",
    )
    pickup_time = models.TimeField(null=True, blank=True)
    drop_time = models.TimeField(null=True, blank=True)
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="transport_assignments",
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "transport_assignment"
        verbose_name = _("transport assignment")
        verbose_name_plural = _("transport assignments")

    def __str__(self):
        return f"{self.student} - {self.route}"


class TransportFee(models.Model):
    """Transport fee model."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="transport_fees",
    )
    route = models.ForeignKey(
        TransportRoute, on_delete=models.CASCADE, related_name="fees"
    )
    academic_year = models.ForeignKey(
        "students.AcademicYear",
        on_delete=models.CASCADE,
        related_name="transport_fees",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transport_fee"
        verbose_name = _("transport fee")
        verbose_name_plural = _("transport fees")

    def __str__(self):
        return f"{self.student} - {self.route} - {self.amount}"
