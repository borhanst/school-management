from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import Subject
from roles.decorators import permission_required, permission_required_any
from students.models import AcademicYear, ClassLevel, Section, Student

from .models import ExamSchedule, ExamType, Grade, Term


@login_required
@permission_required("examinations", "view")
def index(request):
    """Dashboard overview of examinations."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {}

    if academic_year:
        # Get exam schedule statistics
        total_schedules = ExamSchedule.objects.filter(
            academic_year=academic_year
        ).count()

        # Get upcoming exams (next 7 days)
        from datetime import date, timedelta

        today = date.today()
        week_later = today + timedelta(days=7)
        upcoming_exams = ExamSchedule.objects.filter(
            academic_year=academic_year,
            date__gte=today,
            date__lte=week_later,
        ).order_by("date", "start_time")[:5]

        context.update(
            {
                "total_schedules": total_schedules,
                "upcoming_exams": upcoming_exams,
            }
        )

    return render(request, "examinations/index.html", context)


@login_required
@permission_required("examinations", "view")
def grades(request):
    """Grade entry and viewing."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {"academic_year": academic_year}

    if academic_year:
        exam_types = ExamType.objects.filter(
            academic_year=academic_year, is_active=True
        )
        terms = Term.objects.filter(academic_year=academic_year, is_active=True)

        # Get class levels through sections for the academic year
        sections = Section.objects.filter(
            academic_year=academic_year, is_active=True
        ).select_related("class_level")

        class_levels = ClassLevel.objects.filter(
            sections__academic_year=academic_year, sections__is_active=True
        ).distinct()

        context.update(
            {
                "exam_types": exam_types,
                "terms": terms,
                "class_levels": class_levels,
            }
        )

        # Get grades if filters are applied
        exam_type_id = request.GET.get("exam_type")
        class_level_id = request.GET.get("class_level")
        subject_id = request.GET.get("subject")

        if exam_type_id and class_level_id:
            grades_qs = Grade.objects.filter(academic_year=academic_year)

            if exam_type_id:
                grades_qs = grades_qs.filter(exam_type_id=exam_type_id)
            if class_level_id:
                grades_qs = grades_qs.filter(
                    subject__class_level_id=class_level_id
                )
            if subject_id:
                grades_qs = grades_qs.filter(subject_id=subject_id)

            context["grades"] = grades_qs.select_related(
                "student__user", "subject", "exam_type"
            )[:50]

    return render(request, "examinations/grades.html", context)


@login_required
@permission_required_any(
    ("examinations", "add"), ("examinations", "edit")
)
def grade_entry(request):
    """Grade entry form for a specific exam and subject."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        messages.error(request, "No active academic year found.")
        return redirect("examinations:grades")

    if request.method == "POST":
        exam_type_id = request.POST.get("exam_type")
        subject_id = request.POST.get("subject")
        class_level_id = request.POST.get("class_level")

        if not all([exam_type_id, subject_id, class_level_id]):
            messages.error(request, "Please select all required fields.")
            return redirect("examinations:grade_entry")

        exam_type = get_object_or_404(ExamType, id=exam_type_id)
        subject = get_object_or_404(Subject, id=subject_id)
        class_level = get_object_or_404(ClassLevel, id=class_level_id)

        # Get students in this class
        students = Student.objects.filter(
            academic_year=academic_year,
            class_level=class_level,
            is_active=True,
        ).select_related("user")

        # Process grade entries
        for student in students:
            marks_key = f"marks_{student.id}"
            remarks_key = f"remarks_{student.id}"

            if marks_key in request.POST:
                marks = request.POST.get(marks_key)
                remarks = request.POST.get(remarks_key, "")

                if marks:
                    # Calculate grade letter
                    try:
                        marks_value = float(marks)
                        grade_letter = calculate_grade(marks_value)
                    except ValueError:
                        grade_letter = "F"

                    # Create or update grade
                    Grade.objects.update_or_create(
                        student=student,
                        subject=subject,
                        exam_type=exam_type,
                        academic_year=academic_year,
                        defaults={
                            "marks": marks,
                            "grade_letter": grade_letter,
                            "remarks": remarks,
                            "entered_by": (
                                request.user.teacher_profile
                                if hasattr(request.user, "teacher_profile")
                                else None
                            ),
                        },
                    )

        messages.success(request, "Grades saved successfully.")
        return redirect("examinations:grades")

    # GET request - show grade entry form
    exam_types = ExamType.objects.filter(
        academic_year=academic_year, is_active=True
    )
    class_levels = ClassLevel.objects.filter(academic_year=academic_year)

    context = {
        "exam_types": exam_types,
        "class_levels": class_levels,
        "academic_year": academic_year,
    }

    # If filters are applied, show students
    exam_type_id = request.GET.get("exam_type")
    subject_id = request.GET.get("subject")
    class_level_id = request.GET.get("class_level")

    if exam_type_id and subject_id and class_level_id:
        subject = get_object_or_404(Subject, id=subject_id)
        class_level = get_object_or_404(ClassLevel, id=class_level_id)

        students = Student.objects.filter(
            academic_year=academic_year,
            class_level=class_level,
            is_active=True,
        ).select_related("user")

        # Get existing grades
        existing_grades = Grade.objects.filter(
            academic_year=academic_year,
            exam_type_id=exam_type_id,
            subject_id=subject_id,
            student__in=students,
        )

        grade_dict = {g.student_id: g for g in existing_grades}

        # Add grades to students
        for student in students:
            student.grade = grade_dict.get(student.id)

        context.update(
            {
                "selected_exam_type": exam_type_id,
                "selected_subject": subject_id,
                "selected_class_level": class_level_id,
                "subject": subject,
                "class_level": class_level,
                "students": students,
            }
        )

    return render(request, "examinations/grade_entry.html", context)


def calculate_grade(marks):
    """Calculate grade letter based on marks."""
    if marks >= 90:
        return "A+"
    elif marks >= 80:
        return "A"
    elif marks >= 70:
        return "A-"
    elif marks >= 60:
        return "B+"
    elif marks >= 50:
        return "B"
    elif marks >= 40:
        return "B-"
    elif marks >= 30:
        return "C+"
    elif marks >= 20:
        return "C"
    elif marks >= 10:
        return "C-"
    else:
        return "F"


@login_required
@permission_required_any(
    ("examinations", "add"), ("examinations", "edit")
)
def get_subjects(request):
    """Get subjects for a class level (AJAX)."""
    class_level_id = request.GET.get("class_level_id")

    if not class_level_id:
        return JsonResponse({"subjects": []})

    subjects = Subject.objects.filter(
        class_level_id=class_level_id, is_active=True
    ).values("id", "name", "code")

    return JsonResponse({"subjects": list(subjects)})


@login_required
@permission_required_any(
    ("examinations", "add"), ("examinations", "edit")
)
def get_students_for_grade(request):
    """Get students for grade entry (AJAX)."""
    class_level_id = request.GET.get("class_level_id")
    academic_year_id = request.GET.get("academic_year_id")

    if not class_level_id or not academic_year_id:
        return JsonResponse({"students": []})

    students = Student.objects.filter(
        academic_year_id=academic_year_id,
        class_level_id=class_level_id,
        is_active=True,
    ).select_related("user")

    student_data = [
        {
            "id": s.id,
            "name": s.user.get_full_name() or s.user.username,
            "roll_number": s.roll_number,
        }
        for s in students
    ]

    return JsonResponse({"students": student_data})


@login_required
@permission_required("examinations", "view")
def schedule(request):
    """Exam schedule list and management."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {"academic_year": academic_year}

    if academic_year:
        exam_types = ExamType.objects.filter(
            academic_year=academic_year, is_active=True
        )
        # Get class levels through sections for the academic year
        class_levels = ClassLevel.objects.filter(
            sections__academic_year=academic_year, sections__is_active=True
        ).distinct()

        context.update(
            {
                "exam_types": exam_types,
                "class_levels": class_levels,
            }
        )

        # Get schedules with filters
        schedules = ExamSchedule.objects.filter(
            academic_year=academic_year
        ).select_related("exam_type", "subject", "class_level")

        exam_type_id = request.GET.get("exam_type")
        class_level_id = request.GET.get("class_level")

        if exam_type_id:
            schedules = schedules.filter(exam_type_id=exam_type_id)
        if class_level_id:
            schedules = schedules.filter(class_level_id=class_level_id)

        context["schedules"] = schedules

    return render(request, "examinations/schedule.html", context)


@login_required
@permission_required("examinations", "add")
def schedule_add(request):
    """Add new exam schedule."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        messages.error(request, "No active academic year found.")
        return redirect("examinations:schedule")

    if request.method == "POST":
        exam_type_id = request.POST.get("exam_type")
        subject_id = request.POST.get("subject")
        class_level_id = request.POST.get("class_level")
        date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        marks = request.POST.get("marks")
        room_no = request.POST.get("room_no", "")
        instructions = request.POST.get("instructions", "")

        if not all(
            [
                exam_type_id,
                subject_id,
                class_level_id,
                date,
                start_time,
                end_time,
                marks,
            ]
        ):
            messages.error(request, "Please fill all required fields.")
            return redirect("examinations:schedule_add")

        exam_type = get_object_or_404(ExamType, id=exam_type_id)
        subject = get_object_or_404(Subject, id=subject_id)
        class_level = get_object_or_404(ClassLevel, id=class_level_id)

        # Check for duplicate
        if ExamSchedule.objects.filter(
            exam_type=exam_type,
            subject=subject,
            class_level=class_level,
            academic_year=academic_year,
        ).exists():
            messages.error(
                request,
                "An exam schedule already exists for this exam type, subject, and class.",
            )
            return redirect("examinations:schedule_add")

        ExamSchedule.objects.create(
            exam_type=exam_type,
            subject=subject,
            class_level=class_level,
            academic_year=academic_year,
            date=date,
            start_time=start_time,
            end_time=end_time,
            marks=marks,
            room_no=room_no,
            instructions=instructions,
        )

        messages.success(request, "Exam schedule created successfully.")
        return redirect("examinations:schedule")

    # GET request
    exam_types = ExamType.objects.filter(
        academic_year=academic_year, is_active=True
    )
    # Get class levels through sections for the academic year
    class_levels = ClassLevel.objects.filter(
        sections__academic_year=academic_year, sections__is_active=True
    ).distinct()

    context = {
        "exam_types": exam_types,
        "class_levels": class_levels,
        "academic_year": academic_year,
    }

    return render(request, "examinations/schedule_form.html", context)


@login_required
@permission_required("examinations", "edit")
def schedule_edit(request, pk):
    """Edit existing exam schedule."""
    schedule = get_object_or_404(ExamSchedule, id=pk)

    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    if request.method == "POST":
        exam_type_id = request.POST.get("exam_type")
        subject_id = request.POST.get("subject")
        class_level_id = request.POST.get("class_level")
        date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        marks = request.POST.get("marks")
        room_no = request.POST.get("room_no", "")
        instructions = request.POST.get("instructions", "")

        if not all(
            [
                exam_type_id,
                subject_id,
                class_level_id,
                date,
                start_time,
                end_time,
                marks,
            ]
        ):
            messages.error(request, "Please fill all required fields.")
            return redirect("examinations:schedule_edit", pk=pk)

        exam_type = get_object_or_404(ExamType, id=exam_type_id)
        subject = get_object_or_404(Subject, id=subject_id)
        class_level = get_object_or_404(ClassLevel, id=class_level_id)

        # Check for duplicate (excluding current)
        if (
            ExamSchedule.objects.filter(
                exam_type=exam_type,
                subject=subject,
                class_level=class_level,
                academic_year=academic_year,
            )
            .exclude(id=pk)
            .exists()
        ):
            messages.error(
                request,
                "An exam schedule already exists for this exam type, subject, and class.",
            )
            return redirect("examinations:schedule_edit", pk=pk)

        schedule.exam_type = exam_type
        schedule.subject = subject
        schedule.class_level = class_level
        schedule.date = date
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.marks = marks
        schedule.room_no = room_no
        schedule.instructions = instructions
        schedule.save()

        messages.success(request, "Exam schedule updated successfully.")
        return redirect("examinations:schedule")

    # GET request
    exam_types = (
        ExamType.objects.filter(academic_year=academic_year, is_active=True)
        if academic_year
        else ExamType.objects.none()
    )
    class_levels = (
        ClassLevel.objects.filter(
            sections__academic_year=academic_year, sections__is_active=True
        ).distinct()
        if academic_year
        else ClassLevel.objects.none()
    )

    context = {
        "schedule": schedule,
        "exam_types": exam_types,
        "class_levels": class_levels,
        "academic_year": academic_year,
    }

    return render(request, "examinations/schedule_form.html", context)


@login_required
@permission_required("examinations", "delete")
def schedule_delete(request, pk):
    """Delete exam schedule."""
    schedule = get_object_or_404(ExamSchedule, id=pk)

    if request.method == "POST":
        schedule.delete()
        messages.success(request, "Exam schedule deleted successfully.")
        return redirect("examinations:schedule")

    return render(
        request,
        "examinations/schedule_confirm_delete.html",
        {"schedule": schedule},
    )


@login_required
@permission_required("examinations", "view")
def report_card(request):
    """Report card view."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {"academic_year": academic_year}

    if academic_year:
        exam_types = ExamType.objects.filter(
            academic_year=academic_year, is_active=True
        )
        terms = Term.objects.filter(academic_year=academic_year, is_active=True)
        # Get class levels through sections for the academic year
        class_levels = ClassLevel.objects.filter(
            sections__academic_year=academic_year, sections__is_active=True
        ).distinct()

        context.update(
            {
                "exam_types": exam_types,
                "terms": terms,
                "class_levels": class_levels,
            }
        )

        # Get grades for report card
        exam_type_id = request.GET.get("exam_type")
        term_id = request.GET.get("term")
        student_id = request.GET.get("student")

        if student_id:
            student = get_object_or_404(
                Student.objects.select_related("user", "class_level"),
                id=student_id,
                academic_year=academic_year,
            )

            grades = Grade.objects.filter(
                student=student,
                academic_year=academic_year,
            ).select_related("subject", "exam_type")

            if exam_type_id:
                grades = grades.filter(exam_type_id=exam_type_id)
            if term_id:
                grades = grades.filter(term_id=term_id)

            context.update(
                {
                    "student": student,
                    "grades": grades,
                }
            )
        elif class_levels:
            # Show students for class selection
            class_level_id = request.GET.get("class_level")
            if class_level_id:
                students = Student.objects.filter(
                    academic_year=academic_year,
                    class_level_id=class_level_id,
                    is_active=True,
                ).select_related("user")
                context["students"] = students
                context["selected_class_level"] = class_level_id

    return render(request, "examinations/report_card.html", context)


@login_required
@permission_required("examinations", "view")
def my_exams(request):
    """View exams for current student."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    context = {"academic_year": academic_year}

    if academic_year and hasattr(request.user, "student_profile"):
        student = request.user.student_profile

        # Get upcoming exams for student's class
        from datetime import date

        today = date.today()
        upcoming_exams = ExamSchedule.objects.filter(
            class_level=student.class_level,
            date__gte=today,
        ).order_by("date", "start_time")

        # Get past exams
        past_exams = ExamSchedule.objects.filter(
            class_level=student.class_level,
            date__lt=today,
        ).order_by("-date", "-start_time")

        # Get grades
        grades = Grade.objects.filter(
            student=student, academic_year=academic_year
        ).select_related("subject", "exam_type")

        context.update(
            {
                "upcoming_exams": upcoming_exams,
                "past_exams": past_exams,
                "grades": grades,
            }
        )

    return render(request, "examinations/my_exams.html", context)
