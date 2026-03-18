from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.shortcuts import render
from django.utils import timezone

from academics.models import Timetable
from attendance.models import Attendance
from examinations.models import ExamSchedule, Grade
from fees.models import FeeInvoice, FeePayment
from library.models import BookIssue
from roles.decorators import permission_required
from students.models import AcademicYear, ClassLevel, Student


@login_required
@permission_required("dashboard", "view")
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
    current_time = timezone.localtime()
    current_weekday = current_time.weekday()
    current_clock = current_time.time()

    # Student stats
    total_students = Student.objects.filter(status="studying").count()
    new_students_today = Student.objects.filter(
        admission_date=today, status="studying"
    ).count()

    # Class-wise student count with live attendance and timetable snapshot
    class_queryset = ClassLevel.objects.filter(is_active=True).annotate(
        student_count=Count("students", filter=Q(students__status="studying"))
    )

    attendance_by_class = {}
    if academic_year:
        attendance_rows = Attendance.objects.filter(
            date=today,
            academic_year=academic_year,
            student__status="studying",
        ).values("student__class_level").annotate(
            marked_students=Count("student", distinct=True),
            present_students=Count(
                "student", filter=Q(status="present"), distinct=True
            ),
        )
        attendance_by_class = {
            row["student__class_level"]: row for row in attendance_rows
        }

    active_timetables = {}
    if academic_year:
        ongoing_slots = (
            Timetable.objects.filter(
                academic_year=academic_year,
                day_of_week=current_weekday,
                period__start_time__lte=current_clock,
                period__end_time__gte=current_clock,
            )
            .select_related("subject", "period", "section__class_level")
            .order_by("section__class_level__numeric_name", "period__period_no")
        )

        for slot in ongoing_slots:
            class_id = slot.section.class_level_id
            slot_bucket = active_timetables.setdefault(
                class_id,
                {
                    "period_no": slot.period.period_no,
                    "subjects": [],
                },
            )
            if slot.subject.name not in slot_bucket["subjects"]:
                slot_bucket["subjects"].append(slot.subject.name)

    class_cards = []
    for class_level in class_queryset:
        attendance_row = attendance_by_class.get(class_level.id, {})
        current_slot = active_timetables.get(class_level.id)

        subject_names = []
        period_label = "No active period"
        if current_slot:
            subject_names = current_slot["subjects"]
            period_label = f"Period {current_slot['period_no']}"

        if not subject_names:
            subject_label = "No subject running now"
        elif len(subject_names) == 1:
            subject_label = subject_names[0]
        elif len(subject_names) == 2:
            subject_label = ", ".join(subject_names)
        else:
            subject_label = (
                f"{', '.join(subject_names[:2])} +{len(subject_names) - 2} more"
            )

        marked_students = attendance_row.get("marked_students", 0)
        present_students = attendance_row.get("present_students", 0)
        attendance_percentage = (
            round((present_students / class_level.student_count) * 100, 1)
            if class_level.student_count > 0
            else 0
        )

        class_cards.append(
            {
                "id": class_level.id,
                "name": class_level.name,
                "student_count": class_level.student_count,
                "present_students": present_students,
                "marked_students": marked_students,
                "attendance_percentage": attendance_percentage,
                "current_period": period_label,
                "current_subject": subject_label,
            }
        )

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
        "class_counts": class_cards,
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
    total_due_amount = (
        fee_invoices.aggregate(total=Sum("due_amount"))["total"] or 0
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
        "total_due_amount": total_due_amount,
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

    today = timezone.localdate()
    # Get children
    children = parent.children.select_related(
        "user", "class_level", "section", "academic_year"
    )
    total_children = children.count()
    total_due_amount = 0
    total_upcoming_exams = 0

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

        fee_due = (
            FeeInvoice.objects.filter(
                student=child, academic_year=academic_year
            ).aggregate(total=Sum("due_amount"))["total"]
            or 0
        )

        upcoming_exams = ExamSchedule.objects.filter(
            class_level=child.class_level,
            date__gte=today,
        ).select_related("subject", "exam_type").order_by("date", "start_time")[
            :3
        ]
        total_upcoming_exams += upcoming_exams.count()
        next_exam = upcoming_exams[0] if upcoming_exams else None

        total_due_amount += fee_due

        children_data.append(
            {
                "student": child,
                "attendance": attendance,
                "fee_due": fee_due,
                "upcoming_exams": upcoming_exams,
                "next_exam": next_exam,
            }
        )

    return {
        "parent": parent,
        "children_data": children_data,
        "total_children": total_children,
        "total_due_amount": total_due_amount,
        "total_upcoming_exams": total_upcoming_exams,
    }
