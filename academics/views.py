from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from roles.decorators import permission_required
from students.models import AcademicYear, ClassLevel, Section

from .models import Subject, Timetable


@login_required
@permission_required("academics", "view")
def classes(request):
    """View all classes (class levels and sections)."""
    class_levels = ClassLevel.objects.prefetch_related("sections").order_by(
        "numeric_name"
    )

    context = {
        "class_levels": class_levels,
    }
    return render(request, "academics/classes.html", context)


@login_required
@permission_required("academics", "view")
def subjects(request):
    """View all subjects."""
    subjects_list = Subject.objects.select_related(
        "class_level", "teacher__user"
    ).order_by("class_level__name", "name")

    context = {
        "subjects": subjects_list,
    }
    return render(request, "academics/subjects.html", context)


@login_required
@permission_required("academics", "view")
def timetable_view(request):
    """View timetable."""
    # Get current academic year
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    # Get all sections
    sections = Section.objects.select_related("class_level").order_by(
        "class_level__numeric_name", "name"
    )

    # Get timetable if academic year exists
    if academic_year:
        timetable = (
            Timetable.objects.filter(academic_year=academic_year)
            .select_related(
                "section__class_level", "subject", "period", "teacher__user"
            )
            .order_by(
                "section__class_level__numeric_name",
                "section__name",
                "day_of_week",
                "period__period_no",
            )
        )

        # Group by section and then by day
        timetable_data = {}
        for slot in timetable:
            section_key = (
                f"{slot.section.class_level.name} - {slot.section.name}"
            )
            if section_key not in timetable_data:
                timetable_data[section_key] = {
                    "section": slot.section,
                    "by_day": {},
                }
            day_name = slot.get_day_of_week_display()
            if day_name not in timetable_data[section_key]["by_day"]:
                timetable_data[section_key]["by_day"][day_name] = []
            timetable_data[section_key]["by_day"][day_name].append(slot)
    else:
        timetable = []
        timetable_data = {}

    context = {
        "sections": sections,
        "timetable": timetable,
        "timetable_data": timetable_data,
        "academic_year": academic_year,
        "current_user": request.user,
    }
    return render(request, "academics/timetable.html", context)


@login_required
@permission_required("academics", "view")
def my_class(request):
    """Student's class timetable view."""
    user = request.user

    if user.role != "student":
        return render(request, "base.html", status=403)

    try:
        student = user.student_profile
    except:
        return render(request, "base.html", status=403)

    # Get current academic year
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    # Get timetable
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
    else:
        timetable = []
        timetable_by_day = {}

    context = {
        "student": student,
        "timetable": timetable,
        "timetable_by_day": timetable_by_day,
        "academic_year": academic_year,
    }

    return render(request, "academics/my_class.html", context)
