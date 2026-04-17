from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from academics.models import Period
from communications.mixins import NoticeCreateMixin
from roles.decorators import (
    PermissionRequiredMixin,
    permission_required,
    permission_required_any,
)
from students.models import AcademicYear, ClassLevel, Section, Student

from .models import (
    Attendance,
    AttendanceSession,
    LeaveRequest,
    TeacherAttendancePermission,
)


def get_teacher_allowed_sections(teacher, academic_year):
    """Get sections that a teacher has permission to mark attendance for."""
    # Admin sees all sections
    if teacher.user.role == "admin":
        return Section.objects.filter(
            academic_year=academic_year, is_active=True
        )

    # Teachers see only their permitted sections
    permissions = TeacherAttendancePermission.objects.filter(
        teacher=teacher, academic_year=academic_year
    ).values_list("section_id", flat=True)

    return Section.objects.filter(
        id__in=permissions, academic_year=academic_year, is_active=True
    )


def teacher_can_mark_attendance(teacher, section, academic_year):
    """Check if a teacher has permission to mark attendance for a section."""
    # Admin can mark attendance for any section
    if teacher.user.role == "admin":
        return True

    # Check if teacher has permission for this section
    return TeacherAttendancePermission.objects.filter(
        teacher=teacher, section=section, academic_year=academic_year
    ).exists()


@login_required
@permission_required("attendance", "view")
def index(request):
    """Dashboard overview of attendance."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {}

    if academic_year:
        # Get attendance statistics
        total_students = Student.objects.filter(
            academic_year=academic_year, is_active=True
        ).count()

        today = date.today()
        today_attendance = Attendance.objects.filter(
            date=today, academic_year=academic_year
        ).count()

        # Get attendance by status for today
        attendance_by_status = (
            Attendance.objects.filter(date=today, academic_year=academic_year)
            .values("status")
            .annotate(count=Count("id"))
        )

        context.update(
            {
                "total_students": total_students,
                "today_attendance": today_attendance,
                "attendance_by_status": attendance_by_status,
            }
        )

    return render(request, "attendance/index.html", context)


@login_required
@permission_required("attendance", "mark")
def mark_attendance(request):
    """Mark attendance for a section."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        messages.error(request, "No active academic year found.")
        return redirect("attendance:mark")

    # Get teacher's allowed sections based on permissions
    allowed_sections = Section.objects.none()

    if hasattr(request.user, "teacher_profile"):
        teacher = request.user.teacher_profile
        allowed_sections = get_teacher_allowed_sections(teacher, academic_year)
        if not allowed_sections.exists():
            messages.warning(
                request,
                "You don't have permission to mark attendance for any class. Please contact admin.",
            )
    elif request.user.role == "admin":
        # Admin can see all sections
        allowed_sections = Section.objects.filter(
            academic_year=academic_year, is_active=True
        ).select_related("class_level", "academic_year")

    # If no permission, show empty list
    if not allowed_sections:
        sections = Section.objects.none()
    else:
        sections = allowed_sections.select_related(
            "class_level", "academic_year"
        )

    periods = Period.objects.all().order_by("period_no")

    # Get selected section, date, period
    section_id = request.GET.get("section")
    selected_date = request.GET.get("date", date.today().strftime("%Y-%m-%d"))
    period_id = request.GET.get("period")

    students = []
    existing_attendance = {}

    if section_id:
        # Verify teacher has permission for this section
        if hasattr(request.user, "teacher_profile"):
            teacher = request.user.teacher_profile
            section = get_object_or_404(
                Section, id=section_id, academic_year=academic_year
            )
            if not teacher_can_mark_attendance(teacher, section, academic_year):
                messages.error(
                    request,
                    "You don't have permission to mark attendance for this section.",
                )
                return redirect("attendance:mark")
        else:
            section = get_object_or_404(
                Section, id=section_id, academic_year=academic_year
            )

        students = (
            Student.objects.filter(
                section=section,
                academic_year=academic_year,
                is_active=True,
                status="studying",
            )
            .select_related("user")
            .order_by("roll_number")
        )

        # Get existing attendance for this section/date/period
        attendance_records = Attendance.objects.filter(
            student__section=section,
            date=selected_date,
            academic_year=academic_year,
        )
        if period_id:
            attendance_records = attendance_records.filter(period_id=period_id)

        existing_attendance = {
            att.student_id: {"status": att.status, "remarks": att.remarks or ""}
            for att in attendance_records
        }

    import json

    existing_attendance_json = json.dumps(existing_attendance)

    context = {
        "sections": sections,
        "periods": periods,
        "students": students,
        "existing_attendance_json": existing_attendance_json,
        "selected_section": section_id,
        "selected_date": selected_date,
        "selected_period": period_id,
    }

    return render(request, "attendance/mark.html", context)


@login_required
@permission_required("attendance", "mark")
def save_attendance(request):
    """Save attendance records."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        return JsonResponse({"error": "No active academic year"}, status=400)

    section_id = request.POST.get("section_id")
    selected_date = request.POST.get("date")
    period_id = request.POST.get("period")
    attendance_data = request.POST.get("attendance_data")

    if not section_id or not selected_date or not attendance_data:
        return JsonResponse({"error": "Missing required fields"}, status=400)

    # Check if teacher has permission to mark attendance for this section
    if hasattr(request.user, "teacher_profile"):
        teacher = request.user.teacher_profile
        section = get_object_or_404(
            Section, id=section_id, academic_year=academic_year
        )
        if not teacher_can_mark_attendance(teacher, section, academic_year):
            return JsonResponse(
                {
                    "error": "You don't have permission to mark attendance for this section."
                },
                status=403,
            )
    elif request.user.role != "admin":
        return JsonResponse(
            {"error": "You don't have permission to mark attendance."},
            status=403,
        )

    import json

    try:
        data = json.loads(attendance_data)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    section = get_object_or_404(
        Section, id=section_id, academic_year=academic_year
    )
    period = None
    if period_id:
        period = get_object_or_404(Period, id=period_id)

    # Get or create attendance session
    session, created = AttendanceSession.objects.get_or_create(
        section=section,
        date=selected_date,
        period=period,
        academic_year=academic_year,
        defaults={
            "marked_by": request.user.teacher_profile
            if hasattr(request.user, "teacher_profile")
            else None
        },
    )

    marker = (
        request.user.teacher_profile
        if hasattr(request.user, "teacher_profile")
        else None
    )
    saved_count = 0
    with transaction.atomic():
        for student_id, record in data.items():
            status = record.get("status", "present")
            remarks = record.get("remarks", "")

            Attendance.objects.update_or_create(
                student_id=student_id,
                date=selected_date,
                period=period,
                academic_year=academic_year,
                defaults={
                    "status": status,
                    "remarks": remarks,
                    "marked_by": marker,
                },
            )
            saved_count += 1

    return JsonResponse(
        {
            "success": True,
            "message": f"Attendance saved for {saved_count} students",
            "saved_count": saved_count,
        }
    )


@login_required
@permission_required("attendance", "view_reports")
def attendance_report(request):
    """View attendance reports."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    classes = ClassLevel.objects.all()
    sections = (
        Section.objects.filter(academic_year=academic_year, is_active=True)
        if academic_year
        else []
    )

    # Filter parameters
    class_id = request.GET.get("class")
    section_id = request.GET.get("section")
    student_id = request.GET.get("student")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    attendances = Attendance.objects.none()
    student = None

    if academic_year:
        filters = Q(academic_year=academic_year)

        if class_id:
            filters &= Q(student__class_level_id=class_id)
        if section_id:
            filters &= Q(student__section_id=section_id)
        if student_id:
            filters &= Q(student_id=student_id)
        if date_from:
            filters &= Q(date__gte=date_from)
        if date_to:
            filters &= Q(date__lte=date_to)

        if filters:
            attendances = (
                Attendance.objects.filter(filters)
                .select_related(
                    "student__user",
                    "student__section",
                    "student__class_level",
                    "period",
                )
                .order_by("-date", "student__roll_number")
            )

        if student_id:
            student = Student.objects.select_related(
                "user", "section", "class_level"
            ).get(id=student_id)

    # Calculate statistics
    stats = {}
    if academic_year:
        status_counts = {
            row["status"]: row["count"]
            for row in attendances.values("status").annotate(count=Count("id"))
        }
        total = sum(status_counts.values())
        stats["total"] = total
        stats["present"] = status_counts.get("present", 0)
        stats["absent"] = status_counts.get("absent", 0)
        stats["late"] = status_counts.get("late", 0)
        stats["leave"] = status_counts.get("leave", 0)

        if total > 0:
            stats["present_percent"] = round(
                (stats["present"] / total) * 100, 1
            )
            stats["absent_percent"] = round((stats["absent"] / total) * 100, 1)

    paginator = Paginator(attendances, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "classes": classes,
        "sections": sections,
        "attendances": page_obj.object_list,
        "stats": stats,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "student": student,
        "selected_class": class_id,
        "selected_section": section_id,
        "selected_student": student_id,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "attendance/report.html", context)


@login_required
@permission_required("attendance", "mark")
def get_students(request):
    """Get students for a section (AJAX)."""
    section_id = request.GET.get("section_id")

    if not section_id:
        return JsonResponse({"error": "Section ID required"}, status=400)

    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        return JsonResponse({"error": "No active academic year"}, status=400)

    students = (
        Student.objects.filter(
            section_id=section_id,
            academic_year=academic_year,
            is_active=True,
            status="studying",
        )
        .select_related("user")
        .order_by("roll_number")
    )

    data = [
        {
            "id": s.id,
            "name": s.user.get_full_name(),
            "roll_number": s.roll_number,
            "admission_no": s.admission_no,
        }
        for s in students
    ]

    return JsonResponse({"students": data})


@login_required
@permission_required_any(
    ("attendance", "view"), ("attendance", "apply_leave")
)
def leave_request_list(request):
    """List all leave requests."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    status_filter = request.GET.get("status")

    filters = Q()
    if status_filter:
        filters &= Q(status=status_filter)

    # Admins see all requests.
    if request.user.role == "student":
        try:
            student = request.user.student_profile
            filters &= Q(student=student)
        except:
            filters &= Q(id=None)  # No requests
    elif request.user.role == "parent":
        try:
            parent_profile = request.user.parent_profile
            filters &= Q(student__parents=parent_profile)
        except:
            filters &= Q(id=None)  # No linked children
    elif request.user.role == "teacher":
        # Teachers see requests for their sections
        try:
            teacher = request.user.teacher_profile
            from academics.models import TeacherSubjectAssignment

            teacher_sections = TeacherSubjectAssignment.objects.filter(
                teacher=teacher
            ).values_list("section_id", flat=True)
            filters &= Q(student__section_id__in=teacher_sections)
        except:
            filters &= Q(id=None)
    elif request.user.role != "admin":
        filters &= Q(id=None)

    leave_requests = (
        LeaveRequest.objects.filter(filters)
        .select_related(
            "student__user", "student__section", "student__class_level"
        )
        .order_by("-created_at")
    )

    context = {
        "leave_requests": leave_requests,
        "status_filter": status_filter,
    }

    return render(request, "attendance/leave_requests.html", context)


@method_decorator(login_required, name="dispatch")
class LeaveRequestCreateView(PermissionRequiredMixin, NoticeCreateMixin, View):
    """Create a new leave request."""

    module_slug = "attendance"
    permission_codename = "apply_leave"
    template_name = "attendance/leave_request_form.html"
    success_url_name = "attendance:leave_requests"
    notice_roles = ["admin", "teacher"]
    leave_request = None

    def get_success_url(self):
        return self.success_url_name

    def get(self, request):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request):
        from_date = request.POST.get("from_date")
        to_date = request.POST.get("to_date")
        reason = request.POST.get("reason")

        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, "No active academic year found.")
            return redirect(self.get_success_url())

        student = self.get_student_for_request(academic_year)
        if student is None:
            return redirect(self.get_success_url())

        self.leave_request = LeaveRequest.objects.create(
            student=student,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            academic_year=academic_year,
        )
        self.create_notice_from_request()

        messages.success(self.request, "Leave request submitted successfully.")
        return redirect(self.get_success_url())

    def get_context_data(self):
        academic_year = self.get_academic_year()
        students = []
        selected_student = None

        if academic_year:
            if self.request.user.role in {"admin", "teacher"}:
                students = (
                    Student.objects.filter(
                        academic_year=academic_year,
                        is_active=True,
                        status="studying",
                    )
                    .select_related("user", "section", "class_level")
                    .order_by("user__first_name")
                )
            elif self.request.user.role == "parent":
                students = (
                    Student.objects.filter(
                        academic_year=academic_year,
                        is_active=True,
                        status="studying",
                        parents__user=self.request.user,
                    )
                    .select_related("user", "section", "class_level")
                    .order_by("user__first_name")
                )
            elif self.request.user.role == "student":
                selected_student = getattr(
                    self.request.user, "student_profile", None
                )

        return {
            "students": students,
            "selected_student": selected_student,
            "page_title": "New Leave Request",
            "page_description": "Submit a leave request",
            "submit_label": "Submit Request",
            "leave_request": self.leave_request,
        }

    def get_academic_year(self):
        try:
            return AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            return None

    def get_student_for_request(self, academic_year):
        if self.request.user.role == "student":
            try:
                return self.request.user.student_profile
            except Exception:
                messages.error(self.request, "Student profile not found.")
                return None

        student_id = self.request.POST.get("student")
        if not student_id:
            messages.error(self.request, "Please select a student.")
            return None

        if self.request.user.role == "parent":
            try:
                parent_profile = self.request.user.parent_profile
            except Exception:
                messages.error(self.request, "Parent profile not found.")
                return None

            return get_object_or_404(
                Student,
                id=student_id,
                academic_year=academic_year,
                parents=parent_profile,
            )

        return get_object_or_404(
            Student,
            id=student_id,
            academic_year=academic_year,
        )

    def get_notice_title(self):
        return "Leave request submitted"

    def get_notice_content(self):
        student_name = self.leave_request.student.get_full_name()
        return (
            f"{student_name} submitted a leave request from "
            f"{self.leave_request.from_date} to {self.leave_request.to_date}."
        )

    def get_notice_roles(self):
        return self.notice_roles

    def get_notice_classes(self):
        return [self.leave_request.student.class_level_id]


@method_decorator(login_required, name="dispatch")
class ParentPendingLeaveRequestMixin(PermissionRequiredMixin):
    """Restrict leave editing to parent-owned pending requests."""

    module_slug = "attendance"
    permission_codename = "apply_leave"
    leave_request = None

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != "parent":
            messages.error(
                request, "Only parents can update or delete leave requests."
            )
            return redirect("attendance:leave_requests")
        return super().dispatch(request, *args, **kwargs)

    def get_leave_request(self):
        if self.leave_request is not None:
            return self.leave_request

        self.leave_request = get_object_or_404(
            LeaveRequest.objects.select_related(
                "student__user", "student__class_level", "student__section"
            ),
            id=self.kwargs["pk"],
            status="pending",
            student__parents__user=self.request.user,
        )
        return self.leave_request


@method_decorator(login_required, name="dispatch")
class ParentLeaveRequestUpdateView(ParentPendingLeaveRequestMixin, View):
    """Allow parents to update their pending leave requests."""

    template_name = "attendance/leave_request_form.html"

    def get(self, request, pk):
        leave_request = self.get_leave_request()
        return render(request, self.template_name, self.get_context_data(leave_request))

    def post(self, request, pk):
        leave_request = self.get_leave_request()
        from_date = request.POST.get("from_date")
        to_date = request.POST.get("to_date")
        reason = request.POST.get("reason")
        student_id = request.POST.get("student")

        if not student_id:
            messages.error(request, "Please select a student.")
            return redirect("attendance:leave_request_edit", pk=leave_request.id)

        parent_profile = request.user.parent_profile
        student = get_object_or_404(
            Student,
            id=student_id,
            academic_year=leave_request.academic_year,
            parents=parent_profile,
        )

        leave_request.student = student
        leave_request.from_date = from_date
        leave_request.to_date = to_date
        leave_request.reason = reason
        leave_request.save(
            update_fields=["student", "from_date", "to_date", "reason", "updated_at"]
        )

        messages.success(request, "Leave request updated successfully.")
        return redirect("attendance:leave_requests")

    def get_context_data(self, leave_request):
        students = (
            Student.objects.filter(
                academic_year=leave_request.academic_year,
                is_active=True,
                status="studying",
                parents__user=self.request.user,
            )
            .select_related("user", "section", "class_level")
            .order_by("user__first_name")
        )
        return {
            "students": students,
            "selected_student": leave_request.student,
            "leave_request": leave_request,
            "page_title": "Edit Leave Request",
            "page_description": "Update your pending leave request",
            "submit_label": "Update Request",
        }


@method_decorator(login_required, name="dispatch")
class ParentLeaveRequestDeleteView(ParentPendingLeaveRequestMixin, View):
    """Allow parents to delete their pending leave requests."""

    def post(self, request, pk):
        leave_request = self.get_leave_request()
        leave_request.delete()
        messages.success(request, "Leave request deleted successfully.")
        return redirect("attendance:leave_requests")

    def get(self, request, pk):
        return redirect("attendance:leave_requests")


@method_decorator(login_required, name="dispatch")
class LeaveRequestStatusUpdateView(
    PermissionRequiredMixin, NoticeCreateMixin, View
):
    """Shared status update behavior for leave requests."""

    module_slug = "attendance"
    permission_codename = "approve_leave"
    status = None
    success_message = ""
    notice_title = ""
    notice_roles = ["student", "parent"]
    leave_request = None

    def get(self, request, pk):
        return redirect("attendance:leave_requests")

    def post(self, request, pk):
        self.leave_request = get_object_or_404(LeaveRequest, id=pk)
        remarks = request.POST.get("remarks", "")

        self.leave_request.status = self.status
        self.leave_request.approved_by = (
            request.user.teacher_profile
            if hasattr(request.user, "teacher_profile")
            else None
        )
        self.leave_request.remarks = remarks
        self.leave_request.save()
        self.create_notice_from_request()

        messages.success(self.request, self.success_message)
        return redirect("attendance:leave_requests")

    def get_notice_title(self):
        return self.notice_title

    def get_notice_content(self):
        student_name = self.leave_request.student.get_full_name()
        return (
            f"Leave for {student_name} was {self.status} from "
            f"{self.leave_request.from_date} to {self.leave_request.to_date}."
        )

    def get_notice_roles(self):
        return self.notice_roles

    def get_notice_classes(self):
        return [self.leave_request.student.class_level_id]


@method_decorator(login_required, name="dispatch")
class LeaveRequestApproveView(LeaveRequestStatusUpdateView):
    """Approve a leave request."""

    status = "approved"
    success_message = "Leave request approved."
    notice_title = "Leave request approved"


@method_decorator(login_required, name="dispatch")
class LeaveRequestRejectView(LeaveRequestStatusUpdateView):
    """Reject a leave request."""

    status = "rejected"
    success_message = "Leave request rejected."
    notice_title = "Leave request rejected"


leave_request_create = LeaveRequestCreateView.as_view()
leave_request_edit = ParentLeaveRequestUpdateView.as_view()
leave_request_delete = ParentLeaveRequestDeleteView.as_view()
leave_request_approve = LeaveRequestApproveView.as_view()
leave_request_reject = LeaveRequestRejectView.as_view()


@login_required
@permission_required("attendance", "view")
def my_attendance(request):
    """Student's own attendance view."""
    if request.user.role != "student":
        messages.error(request, "This page is for students only.")
        return redirect("dashboard:index")

    try:
        student = request.user.student_profile
    except:
        messages.error(request, "Student profile not found.")
        return redirect("dashboard:index")

    # Get date range for the current month
    today = date.today()
    date_from = request.GET.get(
        "date_from", f"{today.year}-{today.month:02d}-01"
    )
    date_to = request.GET.get("date_to", today.strftime("%Y-%m-%d"))

    attendances = Attendance.objects.filter(
        student=student, date__gte=date_from, date__lte=date_to
    ).order_by("-date")

    # Calculate statistics
    total = attendances.count()
    present = attendances.filter(status="present").count()
    absent = attendances.filter(status="absent").count()
    late = attendances.filter(status="late").count()
    leave = attendances.filter(status="leave").count()

    context = {
        "attendances": attendances,
        "total": total,
        "present": present,
        "absent": absent,
        "late": late,
        "leave": leave,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "attendance/my_attendance.html", context)
