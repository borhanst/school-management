from django.db.models import Sum
from django.utils import timezone


def _build_today_timeline(student, current_time):
    from academics.models import Timetable

    today_timeline = []
    if not student.section:
        return today_timeline

    today_classes = (
        Timetable.objects.filter(
            section=student.section,
            academic_year=student.academic_year,
            day_of_week=current_time.date().weekday(),
        )
        .select_related("subject", "period", "teacher__user")
        .order_by("period__period_no")
    )

    for slot in today_classes:
        start_time = slot.period.start_time
        end_time = slot.period.end_time

        if current_time.time() > end_time:
            status = "completed"
        elif start_time <= current_time.time() <= end_time:
            status = "ongoing"
        else:
            status = "upcoming"

        today_timeline.append({"slot": slot, "status": status})

    return today_timeline


def build_student_profile_summary(student, now=None):
    from attendance.models import Attendance
    from examinations.models import ExamSchedule, Grade
    from fees.models import FeeInvoice

    current_time = now or timezone.localtime()
    today = current_time.date()

    total_attendance = Attendance.objects.filter(
        student=student,
        academic_year=student.academic_year,
    ).count()
    present_days = Attendance.objects.filter(
        student=student,
        status="present",
        academic_year=student.academic_year,
    ).count()
    attendance_percentage = (
        round((present_days / total_attendance) * 100, 2)
        if total_attendance > 0
        else 0
    )

    grades = Grade.objects.filter(
        student=student,
        academic_year=student.academic_year,
    ).select_related("subject", "exam_type")[:5]

    invoices = FeeInvoice.objects.filter(
        student=student,
        academic_year=student.academic_year,
    ).order_by("-created_at")[:5]
    total_due_amount = (
        FeeInvoice.objects.filter(
            student=student,
            academic_year=student.academic_year,
        ).aggregate(total=Sum("due_amount"))["total"]
        or 0
    )

    upcoming_exams = (
        ExamSchedule.objects.filter(
            class_level=student.class_level,
            academic_year=student.academic_year,
            date__gte=today,
        )
        .select_related("subject", "exam_type")
        .order_by("date", "start_time")[:5]
    )

    return {
        "attendance_percentage": attendance_percentage,
        "grades": grades,
        "invoices": invoices,
        "total_due_amount": total_due_amount,
        "upcoming_exams": upcoming_exams,
        "parent_profiles": student.parents.select_related("user"),
        "today_timeline": _build_today_timeline(student, current_time),
        "today_label": today,
    }
