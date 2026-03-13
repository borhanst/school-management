from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from academics.models import Timetable
from attendance.models import Attendance
from examinations.models import Grade
from fees.models import FeeInvoice, FeePayment
from library.models import BookIssue
from students.models import AcademicYear, ClassLevel, Student


@login_required
def dashboard_index(request):
    """Dashboard index view."""
    user = request.user
    today = timezone.now().date()

    # Get current academic year
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {}

    if user.role == "admin":
        context = get_admin_dashboard(academic_year, today)
    elif user.role == "teacher":
        context = get_teacher_dashboard(user, academic_year)
    elif user.role == "student":
        context = get_student_dashboard(user, academic_year)
    elif user.role == "parent":
        context = get_parent_dashboard(user, academic_year)

    context["academic_year"] = academic_year
    return render(request, f"dashboard/{user.role}.html", context)


def get_admin_dashboard(academic_year, today):
    """Get admin dashboard data."""
    # Student stats
    total_students = Student.objects.filter(status="studying").count()
    new_students_today = Student.objects.filter(
        admission_date=today, status="studying"
    ).count()

    # Class-wise student count
    class_counts = ClassLevel.objects.annotate(
        student_count=Count("students", filter=Q(students__status="studying"))
    ).values("name", "student_count")

    # Attendance today
    if academic_year:
        total_present = Attendance.objects.filter(
            date=today, status="present", academic_year=academic_year
        ).count()

        attendance_percentage = 0
        if total_students > 0:
            attendance_percentage = round(
                (total_present / total_students) * 100, 1
            )
    else:
        total_present = 0
        attendance_percentage = 0

    # Fee collection
    if academic_year:
        total_fee_due = (
            FeeInvoice.objects.filter(academic_year=academic_year).aggregate(
                Sum("total_amount")
            )["total_amount__sum"]
            or 0
        )

        total_fee_paid = (
            FeeInvoice.objects.filter(academic_year=academic_year).aggregate(
                Sum("paid_amount")
            )["paid_amount__sum"]
            or 0
        )

        fee_collection_percentage = 0
        if total_fee_due > 0:
            fee_collection_percentage = round(
                (total_fee_paid / total_fee_due) * 100, 1
            )
    else:
        total_fee_due = 0
        total_fee_paid = 0
        fee_collection_percentage = 0

    # Recent payments
    recent_payments = FeePayment.objects.select_related(
        "invoice__student__user"
    ).order_by("-created_at")[:5]

    # Library stats
    books_issued = BookIssue.objects.filter(status="issued").count()
    overdue_books = BookIssue.objects.filter(
        status="issued", due_date__lt=timezone.now().date()
    ).count()

    return {
        "total_students": total_students,
        "new_students_today": new_students_today,
        "class_counts": list(class_counts),
        "total_present": total_present,
        "attendance_percentage": attendance_percentage,
        "total_fee_due": total_fee_due,
        "total_fee_paid": total_fee_paid,
        "fee_collection_percentage": fee_collection_percentage,
        "recent_payments": recent_payments,
        "books_issued": books_issued,
        "overdue_books": overdue_books,
    }


def get_teacher_dashboard(user, academic_year):
    """Get teacher dashboard data."""
    try:
        teacher = user.teacher_profile
    except:
        teacher = None

    # Classes taught
    if teacher:
        from academics.models import TeacherSubjectAssignment

        classes_taught = TeacherSubjectAssignment.objects.filter(
            teacher=teacher, academic_year=academic_year
        ).select_related("subject", "section__class_level")
    else:
        classes_taught = []

    # Pending grades
    pending_grades = 0

    # Today's timetable
    today_timetable = []
    current_time = timezone.now()
    current_day = current_time.date().weekday()  # 0=Monday, 6=Sunday
    today = current_time.date()

    if teacher and academic_year:
        from academics.models import TeacherSubjectAssignment, Timetable

        # Get teacher's subject assignments
        teacher_assignments = TeacherSubjectAssignment.objects.filter(
            teacher=teacher, academic_year=academic_year
        ).select_related("subject", "section__class_level")

        # Get sections the teacher teaches
        teacher_sections = list(
            teacher_assignments.values_list("section__id", flat=True)
        )

        if teacher_sections:
            # Get today's timetable for these sections
            today_timetable = (
                Timetable.objects.filter(
                    section__id__in=teacher_sections,
                    day_of_week=current_day,
                    academic_year=academic_year,
                )
                .select_related("subject", "period", "section__class_level")
                .order_by("period__period_no")
            )

            # Add status to each timetable slot
            timetable_with_status = []
            for slot in today_timetable:
                start_time = slot.period.start_time
                end_time = slot.period.end_time

                # Determine class status
                if current_time.time() >= end_time:
                    status = "completed"
                elif current_time.time() >= start_time:
                    status = "ongoing"
                else:
                    status = "upcoming"

                timetable_with_status.append(
                    {
                        "slot": slot,
                        "status": status,
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                )

            today_timetable = timetable_with_status

    return {
        "teacher": teacher,
        "classes_taught": classes_taught,
        "pending_grades": pending_grades,
        "today_timetable": today_timetable,
    }


def get_student_dashboard(user, academic_year):
    """Get student dashboard data."""
    try:
        student = user.student_profile
    except:
        return {}

    # Attendance
    if academic_year:
        total_attendance = Attendance.objects.filter(
            student=student, academic_year=academic_year
        ).count()

        present_days = Attendance.objects.filter(
            student=student, academic_year=academic_year, status="present"
        ).count()

        attendance_percentage = (
            round((present_days / total_attendance) * 100, 2)
            if total_attendance > 0
            else 0
        )
    else:
        attendance_percentage = 0

    # Grades
    grades = Grade.objects.filter(
        student=student, academic_year=academic_year
    ).select_related("subject", "exam_type")[:5]

    # Fee status
    fee_invoices = FeeInvoice.objects.filter(
        student=student, academic_year=academic_year
    )

    # Class Timetable
    if academic_year and student.section:
        timetable = (
            Timetable.objects.filter(
                section=student.section, academic_year=academic_year
            )
            .select_related("subject", "period", "teacher__user")
            .order_by("day_of_week", "period__period_no")
        )

        # Group by day
        timetable_by_day = {}
        for slot in timetable:
            day_name = slot.get_day_of_week_display()
            if day_name not in timetable_by_day:
                timetable_by_day[day_name] = []
            timetable_by_day[day_name].append(slot)

        # Get current and next class
        current_time = timezone.now()
        current_day = current_time.date().weekday()  # 0=Monday, 6=Sunday

        current_class = None
        next_class = None

        # Get today's timetable for the student
        today_timetable = timetable.filter(day_of_week=current_day)

        for slot in today_timetable:
            start_time = slot.period.start_time
            end_time = slot.period.end_time

            # Check if class is running (current time is between start and end)
            if start_time <= current_time.time() <= end_time:
                current_class = slot
            # Check for next class (first class that starts after current time)
            elif current_time.time() < start_time and next_class is None:
                next_class = slot

        # If no next class today, get tomorrow's first class
        if next_class is None:
            tomorrow_day = (current_day + 1) % 7
            tomorrow_timetable = timetable.filter(day_of_week=tomorrow_day)
            if tomorrow_timetable:
                next_class = tomorrow_timetable.first()
    else:
        timetable = []
        timetable_by_day = {}
        current_class = None
        next_class = None

    return {
        "student": student,
        "attendance_percentage": attendance_percentage,
        "grades": grades,
        "fee_invoices": fee_invoices,
        "timetable": timetable,
        "timetable_by_day": timetable_by_day,
        "current_class": current_class,
        "next_class": next_class,
    }


def get_parent_dashboard(user, academic_year):
    """Get parent dashboard data."""
    try:
        parent = user.parent_profile
    except:
        return {}

    # Get children
    children = parent.children.all()

    children_data = []
    for child in children:
        # Attendance
        if academic_year:
            total = Attendance.objects.filter(
                student=child, academic_year=academic_year
            ).count()
            present = Attendance.objects.filter(
                student=child, academic_year=academic_year, status="present"
            ).count()
            attendance = round((present / total) * 100, 2) if total > 0 else 0
        else:
            attendance = 0

        # Grades
        grades = Grade.objects.filter(
            student=child, academic_year=academic_year
        )[:3]

        children_data.append(
            {
                "student": child,
                "attendance": attendance,
                "grades": grades,
            }
        )

    return {
        "parent": parent,
        "children_data": children_data,
    }
