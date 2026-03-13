from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import Period
from roles.decorators import permission_required
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

    saved_count = 0
    for student_id, record in data.items():
        status = record.get("status", "present")
        remarks = record.get("remarks", "")

        attendance, att_created = Attendance.objects.update_or_create(
            student_id=student_id,
            date=selected_date,
            period=period,
            academic_year=academic_year,
            defaults={
                "status": status,
                "remarks": remarks,
                "marked_by": request.user.teacher_profile
                if hasattr(request.user, "teacher_profile")
                else None,
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

    attendances = []
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
                    "student__user", "student__section", "student__class_level"
                )
                .order_by("-date", "student__roll_number")
            )

        if student_id:
            student = Student.objects.select_related(
                "user", "section", "class_level"
            ).get(id=student_id)

    # Calculate statistics
    stats = {}
    if attendances:
        total = attendances.count()
        stats["total"] = total
        stats["present"] = attendances.filter(status="present").count()
        stats["absent"] = attendances.filter(status="absent").count()
        stats["late"] = attendances.filter(status="late").count()
        stats["leave"] = attendances.filter(status="leave").count()

        if total > 0:
            stats["present_percent"] = round(
                (stats["present"] / total) * 100, 1
            )
            stats["absent_percent"] = round((stats["absent"] / total) * 100, 1)

    context = {
        "classes": classes,
        "sections": sections,
        "attendances": attendances,
        "stats": stats,
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
@permission_required("attendance", "view")
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

    # Teachers and admins see all requests, students see their own
    if request.user.role == "student":
        try:
            student = request.user.student_profile
            filters &= Q(student=student)
        except:
            filters &= Q(id=None)  # No requests
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
            pass

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


@login_required
@permission_required("attendance", "view")
def leave_request_create(request):
    """Create a new leave request."""
    if request.method == "POST":
        from_date = request.POST.get("from_date")
        to_date = request.POST.get("to_date")
        reason = request.POST.get("reason")

        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, "No active academic year found.")
            return redirect("attendance:leave_requests")

        if request.user.role == "student":
            try:
                student = request.user.student_profile
            except:
                messages.error(request, "Student profile not found.")
                return redirect("attendance:leave_requests")
        else:
            student_id = request.POST.get("student")
            if not student_id:
                messages.error(request, "Please select a student.")
                return redirect("attendance:leave_requests")
            student = get_object_or_404(
                Student, id=student_id, academic_year=academic_year
            )

        leave_request = LeaveRequest.objects.create(
            student=student,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            academic_year=academic_year,
        )

        messages.success(request, "Leave request submitted successfully.")
        return redirect("attendance:leave_requests")

    # GET request - show form
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    students = []
    if academic_year:
        if request.user.role == "admin" or request.user.role == "teacher":
            students = (
                Student.objects.filter(
                    academic_year=academic_year,
                    is_active=True,
                    status="studying",
                )
                .select_related("user", "section", "class_level")
                .order_by("user__first_name")
            )

    return render(
        request,
        "attendance/leave_request_form.html",
        {
            "students": students,
        },
    )


@login_required
@permission_required("attendance", "approve_leave")
def leave_request_approve(request, pk):
    """Approve a leave request."""
    leave_request = get_object_or_404(LeaveRequest, id=pk)

    if request.method == "POST":
        remarks = request.POST.get("remarks", "")

        leave_request.status = "approved"
        leave_request.approved_by = (
            request.user.teacher_profile
            if hasattr(request.user, "teacher_profile")
            else None
        )
        leave_request.remarks = remarks
        leave_request.save()

        messages.success(request, "Leave request approved.")

    return redirect("attendance:leave_requests")


@login_required
@permission_required("attendance", "approve_leave")
def leave_request_reject(request, pk):
    """Reject a leave request."""
    leave_request = get_object_or_404(LeaveRequest, id=pk)

    if request.method == "POST":
        remarks = request.POST.get("remarks", "")

        leave_request.status = "rejected"
        leave_request.approved_by = (
            request.user.teacher_profile
            if hasattr(request.user, "teacher_profile")
            else None
        )
        leave_request.remarks = remarks
        leave_request.save()

        messages.success(request, "Leave request rejected.")

    return redirect("attendance:leave_requests")


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
