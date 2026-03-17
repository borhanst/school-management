from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import TeacherProfile
from roles.decorators import permission_required
from students.models import AcademicYear, ClassLevel, Section, Student

from .forms import ClassLevelForm, SectionForm, SubjectForm, TimetableForm
from .models import Subject, TeacherSubjectAssignment, Timetable


def get_user_timetable_sections(user, academic_year):
    """Return sections the user is allowed to see in the timetable."""
    if not academic_year:
        return Section.objects.none()

    base_sections = Section.objects.filter(
        academic_year=academic_year, is_active=True
    ).select_related("class_level")

    if user.role == "admin":
        return base_sections.order_by("class_level__numeric_name", "name")

    if user.role == "teacher" and hasattr(user, "teacher_profile"):
        assigned_section_ids = TeacherSubjectAssignment.objects.filter(
            teacher=user.teacher_profile,
            academic_year=academic_year,
            section__is_active=True,
        ).values_list("section_id", flat=True)
        return base_sections.filter(id__in=assigned_section_ids).order_by(
            "class_level__numeric_name", "name"
        )

    if user.role == "student" and hasattr(user, "student_profile"):
        student_section_id = user.student_profile.section_id
        if not student_section_id:
            return Section.objects.none()
        return base_sections.filter(id=student_section_id).order_by(
            "class_level__numeric_name", "name"
        )

    return Section.objects.none()


@login_required
@permission_required("academics", "view")
def classes(request):
    """View all classes (class levels and sections)."""
    current_academic_year = AcademicYear.objects.filter(is_current=True).first()
    sections_queryset = Section.objects.select_related(
        "academic_year"
    ).annotate(
        total_students=Count(
            "students",
            filter=Q(
                students__status="studying",
                students__is_active=True,
            ),
        )
    )
    if current_academic_year:
        sections_queryset = sections_queryset.filter(
            academic_year=current_academic_year
        )

    class_levels = (
        ClassLevel.objects.prefetch_related(
            Prefetch("sections", queryset=sections_queryset)
        )
        .annotate(
            total_students=Count(
                "students",
                filter=Q(
                    students__status="studying",
                    students__is_active=True,
                ),
                distinct=True,
            ),
            students_without_section=Count(
                "students",
                filter=Q(
                    students__status="studying",
                    students__is_active=True,
                    students__section__isnull=True,
                ),
                distinct=True,
            ),
        )
        .order_by("numeric_name")
    )
    total_students = sum(level.total_students for level in class_levels)
    total_unassigned_students = sum(
        level.students_without_section for level in class_levels
    )

    context = {
        "class_levels": class_levels,
        "current_academic_year": current_academic_year,
        "total_students": total_students,
        "total_unassigned_students": total_unassigned_students,
    }
    return render(request, "academics/classes.html", context)


@login_required
@permission_required("academics", "view")
def class_detail(request, pk):
    """Show full details for a class level."""
    current_academic_year = AcademicYear.objects.filter(is_current=True).first()

    sections_queryset = Section.objects.select_related("academic_year").annotate(
        total_students=Count(
            "students",
            filter=Q(
                students__status="studying",
                students__is_active=True,
            ),
        )
    )
    if current_academic_year:
        sections_queryset = sections_queryset.filter(
            academic_year=current_academic_year
        )

    class_level = get_object_or_404(
        ClassLevel.objects.prefetch_related(
            Prefetch("sections", queryset=sections_queryset),
            Prefetch(
                "subjects",
                queryset=Subject.objects.select_related("teacher__user")
                .filter(is_active=True)
                .order_by("name"),
            ),
        ).annotate(
            total_students=Count(
                "students",
                filter=Q(
                    students__status="studying",
                    students__is_active=True,
                ),
                distinct=True,
            ),
            students_without_section=Count(
                "students",
                filter=Q(
                    students__status="studying",
                    students__is_active=True,
                    students__section__isnull=True,
                ),
                distinct=True,
            ),
        ),
        pk=pk,
    )

    students = (
        Student.objects.select_related("user", "section", "academic_year")
        .filter(
            class_level=class_level,
            status="studying",
            is_active=True,
        )
        .order_by("section__name", "roll_number", "admission_no")
    )
    if current_academic_year:
        students = students.filter(academic_year=current_academic_year)

    context = {
        "class_level": class_level,
        "current_academic_year": current_academic_year,
        "students": students,
    }
    return render(request, "academics/class_detail.html", context)


@login_required
@permission_required("academics", "add")
def class_create(request):
    """Create a class level."""
    form = ClassLevelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Class created successfully.")
        return redirect("academics:classes")
    return render(
        request, "academics/class_form.html", {"form": form, "object": None}
    )


@login_required
@permission_required("academics", "edit")
def class_edit(request, pk):
    """Update a class level."""
    class_level = get_object_or_404(ClassLevel, pk=pk)
    form = ClassLevelForm(request.POST or None, instance=class_level)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Class updated successfully.")
        return redirect("academics:classes")
    return render(
        request,
        "academics/class_form.html",
        {"form": form, "object": class_level},
    )


@login_required
@permission_required("academics", "delete")
def class_delete(request, pk):
    """Delete a class level."""
    class_level = get_object_or_404(ClassLevel, pk=pk)
    if request.method == "POST":
        class_level.delete()
        messages.success(request, "Class deleted successfully.")
        return redirect("academics:classes")
    return render(
        request,
        "academics/confirm_delete.html",
        {
            "object": class_level,
            "title": "Delete Class",
            "cancel_url": "academics:classes",
        },
    )


@login_required
@permission_required("academics", "add")
def section_create(request):
    """Create a section for a class."""
    form = SectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Section created successfully.")
        return redirect("academics:classes")
    return render(
        request,
        "academics/section_form.html",
        {"form": form, "object": None},
    )


@login_required
@permission_required("academics", "view")
def subjects(request):
    """View all subjects."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    class_levels = ClassLevel.objects.none()
    sections = Section.objects.none()
    teachers = TeacherProfile.objects.none()
    selected_class_level = request.GET.get("class_level", "").strip()
    selected_section = request.GET.get("section", "").strip()
    selected_teacher = request.GET.get("teacher", "").strip()

    base_subjects = Subject.objects.select_related(
        "class_level", "teacher__user"
    )
    assignment_queryset = TeacherSubjectAssignment.objects.select_related(
        "section__class_level", "teacher__user"
    )
    if academic_year:
        assignment_queryset = assignment_queryset.filter(
            academic_year=academic_year
        )

    if request.user.role == "teacher" and hasattr(
        request.user, "teacher_profile"
    ):
        teachers = TeacherProfile.objects.filter(
            pk=request.user.teacher_profile.pk
        ).select_related("user")
        teacher_assignments = assignment_queryset.filter(
            teacher=request.user.teacher_profile,
            section__is_active=True,
        )
        sections = Section.objects.filter(
            id__in=teacher_assignments.values_list("section_id", flat=True)
        ).select_related("class_level").order_by(
            "class_level__numeric_name", "name"
        )
        class_levels = ClassLevel.objects.filter(
            sections__in=sections
        ).distinct().order_by("numeric_name")
        base_subjects = base_subjects.filter(
            teacher_assignments__in=teacher_assignments
        ).distinct()

        if not selected_class_level and not selected_section:
            first_section = sections.first()
            if first_section is not None:
                selected_class_level = str(first_section.class_level_id)
        selected_teacher = str(request.user.teacher_profile.pk)
    elif request.user.role == "student" and hasattr(
        request.user, "student_profile"
    ):
        student = request.user.student_profile
        if student.section_id:
            sections = Section.objects.filter(id=student.section_id).select_related(
                "class_level"
            )
            class_levels = ClassLevel.objects.filter(
                id=student.class_level_id
            ).order_by("numeric_name")
            base_subjects = base_subjects.filter(
                teacher_assignments__section_id=student.section_id
            ).distinct()
            selected_class_level = str(student.class_level_id)
            selected_section = str(student.section_id)
        else:
            class_levels = ClassLevel.objects.filter(
                id=student.class_level_id
            ).order_by("numeric_name")
            base_subjects = base_subjects.filter(
                class_level_id=student.class_level_id
            )
            selected_class_level = str(student.class_level_id)
    else:
        class_levels = ClassLevel.objects.filter(is_active=True).order_by(
            "numeric_name"
        )
        sections = Section.objects.select_related("class_level").filter(
            is_active=True
        )
        teachers = TeacherProfile.objects.select_related("user").order_by(
            "user__first_name", "user__last_name", "employee_id"
        )
        if academic_year:
            sections = sections.filter(academic_year=academic_year)

    subjects_list = base_subjects
    visible_assignments = assignment_queryset
    if selected_class_level:
        subjects_list = subjects_list.filter(class_level_id=selected_class_level)
        sections = sections.filter(class_level_id=selected_class_level)
        visible_assignments = visible_assignments.filter(
            section__class_level_id=selected_class_level
        )
    if selected_section:
        subjects_list = subjects_list.filter(
            teacher_assignments__section_id=selected_section
        ).distinct()
        visible_assignments = visible_assignments.filter(
            section_id=selected_section
        )
    if selected_teacher:
        subjects_list = subjects_list.filter(teacher_id=selected_teacher)
        visible_assignments = visible_assignments.filter(
            teacher_id=selected_teacher
        )

    subjects_list = subjects_list.prefetch_related(
        Prefetch(
            "teacher_assignments",
            queryset=visible_assignments.order_by(
                "section__class_level__numeric_name", "section__name"
            ),
        )
    ).order_by("class_level__numeric_name", "name")

    context = {
        "academic_year": academic_year,
        "subjects": subjects_list,
        "class_levels": class_levels,
        "sections": sections,
        "teachers": teachers,
        "selected_class_level": selected_class_level,
        "selected_section": selected_section,
        "selected_teacher": selected_teacher,
    }
    return render(request, "academics/subjects.html", context)


@login_required
@permission_required("academics", "add")
def subject_create(request):
    """Create a subject."""
    form = SubjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Subject created successfully.")
        return redirect("academics:subjects")
    return render(
        request,
        "academics/subject_form.html",
        {"form": form, "object": None},
    )


@login_required
@permission_required("academics", "edit")
def subject_edit(request, pk):
    """Update a subject."""
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST or None, instance=subject)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Subject updated successfully.")
        return redirect("academics:subjects")
    return render(
        request,
        "academics/subject_form.html",
        {"form": form, "object": subject},
    )


@login_required
@permission_required("academics", "delete")
def subject_delete(request, pk):
    """Delete a subject."""
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        subject.delete()
        messages.success(request, "Subject deleted successfully.")
        return redirect("academics:subjects")
    return render(
        request,
        "academics/confirm_delete.html",
        {
            "object": subject,
            "title": "Delete Subject",
            "cancel_url": "academics:subjects",
        },
    )


@login_required
@permission_required("academics", "view")
def timetable_view(request):
    """View timetable."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    sections = get_user_timetable_sections(request.user, academic_year)
    selected_class_level = request.GET.get("class_level", "").strip()
    selected_section = request.GET.get("section", "").strip()
    class_levels = ClassLevel.objects.none()

    if academic_year:
        class_levels = ClassLevel.objects.filter(
            sections__in=sections
        ).distinct().order_by("numeric_name")

        filtered_sections = sections
        if selected_class_level:
            filtered_sections = filtered_sections.filter(
                class_level_id=selected_class_level
            )
        if selected_section:
            filtered_sections = filtered_sections.filter(id=selected_section)

        timetable = (
            Timetable.objects.filter(
                academic_year=academic_year,
                section__in=filtered_sections,
            )
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
        "class_levels": class_levels,
        "timetable": timetable,
        "timetable_data": timetable_data,
        "academic_year": academic_year,
        "current_user": request.user,
        "selected_class_level": selected_class_level,
        "selected_section": selected_section,
    }
    return render(request, "academics/timetable.html", context)


@login_required
@permission_required("academics", "add")
def timetable_create(request):
    """Create a timetable slot."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        messages.error(request, "No active academic year found.")
        return redirect("academics:timetable")

    form = TimetableForm(request.POST or None, academic_year=academic_year)
    if request.method == "POST" and form.is_valid():
        timetable = form.save(commit=False)
        timetable.academic_year = academic_year
        timetable.save()
        messages.success(request, "Timetable entry created successfully.")
        return redirect("academics:timetable")
    return render(
        request,
        "academics/timetable_form.html",
        {"form": form, "object": None, "academic_year": academic_year},
    )


@login_required
@permission_required("academics", "edit")
def timetable_edit(request, pk):
    """Update a timetable slot."""
    timetable = get_object_or_404(Timetable, pk=pk)
    form = TimetableForm(
        request.POST or None,
        instance=timetable,
        academic_year=timetable.academic_year,
    )
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.academic_year = timetable.academic_year
        updated.save()
        messages.success(request, "Timetable entry updated successfully.")
        return redirect("academics:timetable")
    return render(
        request,
        "academics/timetable_form.html",
        {
            "form": form,
            "object": timetable,
            "academic_year": timetable.academic_year,
        },
    )


@login_required
@permission_required("academics", "delete")
def timetable_delete(request, pk):
    """Delete a timetable slot."""
    timetable = get_object_or_404(Timetable, pk=pk)
    if request.method == "POST":
        timetable.delete()
        messages.success(request, "Timetable entry deleted successfully.")
        return redirect("academics:timetable")
    return render(
        request,
        "academics/confirm_delete.html",
        {
            "object": timetable,
            "title": "Delete Timetable Entry",
            "cancel_url": "academics:timetable",
        },
    )


@login_required
@permission_required("academics", "view")
def my_class(request):
    """Student's class timetable view."""
    user = request.user

    if user.role != "student":
        return render(request, "base.html", status=403)

    try:
        student = user.student_profile
    except Exception:
        return render(request, "base.html", status=403)

    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    if academic_year and student.section:
        timetable = (
            Timetable.objects.filter(
                section=student.section, academic_year=academic_year
            )
            .select_related("subject", "period", "teacher__user")
            .order_by("day_of_week", "period__period_no")
        )

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
