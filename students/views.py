import random
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import ListView

from accounts.models import User
from fees.services import create_admission_fee_invoices
from roles.decorators import (
    PermissionRequiredMixin,
    permission_or_role_required,
    permission_required,
)
from roles.services import assign_default_role_to_user

from .forms import StudentCreateForm, StudentUpdateForm
from .models import (
    AcademicYear,
    ClassLevel,
    Section,
    Student,
    StudentPromotionHistory,
)


def generate_admission_no():
    """Generate unique admission number."""
    year = str(timezone.now().year)
    random_digits = "".join(random.choices(string.digits, k=4))
    return f"ADM{year}{random_digits}"


def _filter_students_for_user(queryset, user):
    """Restrict parent users to only their linked children."""
    if user.role != "parent":
        return queryset

    if not hasattr(user, "parent_profile"):
        return queryset.none()

    return queryset.filter(parents=user.parent_profile).distinct()


class StudentListView(PermissionRequiredMixin, ListView):
    """List all students."""

    model = Student
    template_name = "students/list.html"
    context_object_name = "students"
    paginate_by = 20
    module_slug = "students"
    permission_codename = "view"

    def get_queryset(self):
        queryset = Student.objects.select_related(
            "user", "class_level", "section", "academic_year"
        ).filter(status="studying")
        queryset = _filter_students_for_user(queryset, self.request.user)

        # Search
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(admission_no__icontains=search)
            )

        # Filter by class
        class_id = self.request.GET.get("class")
        if class_id:
            queryset = queryset.filter(class_level_id=class_id)

        # Filter by section
        section_id = self.request.GET.get("section")
        if section_id:
            queryset = queryset.filter(section_id=section_id)

        return queryset.order_by("roll_number", "admission_no")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_queryset = _filter_students_for_user(
            Student.objects.filter(status="studying"),
            self.request.user,
        )
        context["classes"] = ClassLevel.objects.filter(
            is_active=True, students__in=student_queryset
        ).distinct()
        context["sections"] = Section.objects.filter(
            is_active=True, students__in=student_queryset
        ).distinct()
        return context


@login_required
@permission_required("students", "add")
def student_create(request):
    """Create a new student."""
    form = StudentCreateForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            created_fee_invoices = {
                "monthly": 0,
                "one_time": 0,
                "total": 0,
            }

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=data["username"],
                        email=data["email"],
                        password=data["password"],
                        role="student",
                        first_name=data["first_name"],
                        last_name=data["last_name"],
                        phone=data["phone"],
                        gender=data["gender"],
                        date_of_birth=data["date_of_birth"],
                    )
                    assign_default_role_to_user(user, assigned_by=request.user)

                    student = Student.objects.create(
                        user=user,
                        admission_no=generate_admission_no(),
                        admission_date=data["admission_date"],
                        date_of_birth=data["date_of_birth"],
                        gender=data["gender"],
                        blood_group=data["blood_group"],
                        religion=data["religion"],
                        aadhar_no=data["aadhar_no"],
                        class_level=data["class_level"],
                        section=data["section"],
                        roll_number=data["roll_number"],
                        academic_year=data["academic_year"],
                        house=data["house"],
                        previous_school=data["previous_school"],
                        tc_no=data["tc_no"],
                        father_name=data.get("father_name", ""),
                        father_phone=data.get("father_phone", ""),
                        father_occupation=data.get("father_occupation", ""),
                        mother_name=data.get("mother_name", ""),
                        mother_phone=data.get("mother_phone", ""),
                        mother_occupation=data.get("mother_occupation", ""),
                        guardian_name=data.get("guardian_name", ""),
                        guardian_phone=data.get("guardian_phone", ""),
                        guardian_relation=data.get("guardian_relation", ""),
                    )

                    if request.user.role == "parent" and hasattr(
                        request.user, "parent_profile"
                    ):
                        request.user.parent_profile.children.add(student)

                    created_fee_invoices = create_admission_fee_invoices(
                        student
                    )
            except IntegrityError:
                form.add_error(
                    "username",
                    "This username is already taken. Please choose another one.",
                )
                messages.error(
                    request, "Please fix the errors below and try again."
                )
                messages.error(
                    request, "Please fix the errors below and try again."
                )
                context = {
                    "form": form,
                    "academic_years": AcademicYear.objects.filter(
                        is_active=True
                    ),
                    "classes": ClassLevel.objects.filter(is_active=True),
                    "sections": Section.objects.filter(
                        is_active=True
                    ).select_related("class_level"),
                }
                return render(request, "students/form.html", context)

            success_message = (
                f"Student {student.get_full_name()} created successfully!"
            )
            if created_fee_invoices["total"]:
                fee_parts = []
                if created_fee_invoices["one_time"]:
                    fee_parts.append(
                        f"{created_fee_invoices['one_time']} admission fee invoice(s)"
                    )
                if created_fee_invoices["monthly"]:
                    fee_parts.append(
                        f"{created_fee_invoices['monthly']} monthly fee invoice(s)"
                    )
                success_message += (
                    " " + " and ".join(fee_parts) + " were created."
                )
            messages.success(request, success_message)
            return redirect("students:list")

        messages.error(request, "Please fix the errors below and try again.")

    # Get context for form
    context = {
        "form": form,
        "academic_years": AcademicYear.objects.filter(is_active=True),
        "classes": ClassLevel.objects.filter(is_active=True),
        "sections": Section.objects.filter(is_active=True).select_related(
            "class_level"
        ),
    }
    return render(request, "students/form.html", context)


@login_required
@permission_or_role_required(permission=("students", "view"), role="parent")
def student_detail(request, pk):
    """Student detail view."""
    student_queryset = Student.objects.select_related(
        "user", "class_level", "section", "academic_year"
    )
    student = get_object_or_404(
        _filter_students_for_user(student_queryset, request.user),
        pk=pk,
    )

    from academics.models import Timetable
    from attendance.models import Attendance
    from examinations.models import ExamSchedule, Grade
    from fees.models import FeeInvoice

    current_time = timezone.localtime()
    today = current_time.date()
    current_weekday = today.weekday()

    # Attendance
    total_attendance = Attendance.objects.filter(
        student=student, academic_year=student.academic_year
    ).count()
    present_days = Attendance.objects.filter(
        student=student, status="present", academic_year=student.academic_year
    ).count()
    attendance_percentage = (
        round((present_days / total_attendance) * 100, 2)
        if total_attendance > 0
        else 0
    )

    # Recent grades
    grades = Grade.objects.filter(
        student=student, academic_year=student.academic_year
    ).select_related("subject", "exam_type")[:5]

    # Fee invoices
    invoices = FeeInvoice.objects.filter(
        student=student, academic_year=student.academic_year
    ).order_by("-created_at")[:5]
    total_due_amount = (
        FeeInvoice.objects.filter(
            student=student, academic_year=student.academic_year
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

    parent_profiles = student.parents.select_related("user")
    today_timeline = []

    if student.section:
        today_classes = (
            Timetable.objects.filter(
                section=student.section,
                academic_year=student.academic_year,
                day_of_week=current_weekday,
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

    context = {
        "student": student,
        "attendance_percentage": attendance_percentage,
        "grades": grades,
        "invoices": invoices,
        "total_due_amount": total_due_amount,
        "upcoming_exams": upcoming_exams,
        "parent_profiles": parent_profiles,
        "today_timeline": today_timeline,
        "today_label": today,
    }
    return render(request, "students/detail.html", context)


@login_required
@permission_required("students", "edit")
def student_update(request, pk):
    """Update student."""
    student = get_object_or_404(Student, pk=pk)
    form = StudentUpdateForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data

            try:
                with transaction.atomic():
                    # Update user
                    student.user.first_name = data["first_name"]
                    student.user.last_name = data["last_name"]
                    student.user.email = data["email"]
                    student.user.phone = data["phone"]
                    student.user.gender = data["gender"]
                    student.user.save()

                    # Update student
                    student.admission_date = data["admission_date"]
                    student.date_of_birth = data["date_of_birth"]
                    student.gender = data["gender"]
                    student.roll_number = data["roll_number"]
                    student.class_level = data["class_level"]
                    student.section = data["section"]
                    student.academic_year = data["academic_year"]
                    student.house = data["house"]
                    student.blood_group = data["blood_group"]
                    student.religion = data["religion"]
                    student.aadhar_no = data["aadhar_no"]
                    student.previous_school = data["previous_school"]
                    student.tc_no = data["tc_no"]
                    student.tc_date = data.get("tc_date")
                    student.father_name = data.get("father_name", "")
                    student.father_phone = data.get("father_phone", "")
                    student.father_occupation = data.get(
                        "father_occupation", ""
                    )
                    student.mother_name = data.get("mother_name", "")
                    student.mother_phone = data.get("mother_phone", "")
                    student.mother_occupation = data.get(
                        "mother_occupation", ""
                    )
                    student.guardian_name = data.get("guardian_name", "")
                    student.guardian_phone = data.get("guardian_phone", "")
                    student.guardian_relation = data.get(
                        "guardian_relation", ""
                    )
                    student.save()
            except IntegrityError:
                form.add_error(
                    None,
                    "An error occurred while updating the student. Please try again.",
                )
                messages.error(
                    request, "Please fix the errors below and try again."
                )
                context = {
                    "student": student,
                    "form": form,
                    "academic_years": AcademicYear.objects.filter(
                        is_active=True
                    ),
                    "classes": ClassLevel.objects.filter(is_active=True),
                    "sections": Section.objects.filter(
                        is_active=True
                    ).select_related("class_level"),
                }
                return render(request, "students/form.html", context)

            messages.success(request, "Student updated successfully!")
            return redirect("students:list")

        messages.error(request, "Please fix the errors below and try again.")

    context = {
        "student": student,
        "form": form,
        "academic_years": AcademicYear.objects.filter(is_active=True),
        "classes": ClassLevel.objects.filter(is_active=True),
        "sections": Section.objects.filter(is_active=True).select_related(
            "class_level"
        ),
    }
    return render(request, "students/form.html", context)


@login_required
@permission_required("students", "delete")
def student_delete(request, pk):
    """Delete student."""
    student = get_object_or_404(Student, pk=pk)

    if request.method == "POST":
        student.user.delete()
        messages.success(request, "Student deleted successfully!")
        return redirect("students:list")

    return render(request, "students/confirm_delete.html", {"student": student})


@login_required
@permission_required("students", "view")
def student_search(request):
    """HTMX search students."""
    query = request.GET.get("q", "")
    class_id = request.GET.get("class", "")

    students = Student.objects.select_related("user", "class_level").filter(
        status="studying"
    )
    students = _filter_students_for_user(students, request.user)

    if query:
        students = students.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(admission_no__icontains=query)
        )

    if class_id:
        students = students.filter(class_level_id=class_id)

    students = students[:10]

    html = render_to_string(
        "students/partials/student_list.html", {"students": students}
    )
    return JsonResponse({"html": html})


@login_required
@permission_required("students", "view")
def get_sections(request):
    """Get sections for a class (HTMX)."""
    class_id = request.GET.get("class_id")
    sections = Section.objects.filter(class_level_id=class_id, is_active=True)

    html = render_to_string(
        "students/partials/section_options.html", {"sections": sections}
    )
    return JsonResponse({"html": html})


@login_required
@permission_required("students", "promote")
def student_promote(request):
    """Promote students to next class."""
    # Get selected class students if any
    selected_class = request.GET.get("from_class")
    students = Student.objects.select_related("user", "class_level").filter(
        status="studying"
    )

    if selected_class:
        students = students.filter(class_level_id=selected_class)
        # Annotate each student with their promotion history count
        from django.db.models import Count

        students = students.annotate(promotion_count=Count("promotions"))
    else:
        students = []

    if request.method == "POST":
        student_ids = request.POST.getlist("students")
        # Get from POST or GET
        to_class = request.POST.get("to_class") or request.GET.get("to_class")
        academic_year_id = request.POST.get("academic_year") or request.GET.get(
            "academic_year"
        )

        # Ensure we have strings, not None
        to_class = str(to_class) if to_class else ""
        academic_year_id = str(academic_year_id) if academic_year_id else ""

        # Build redirect URL with current params
        redirect_url = f"?from_class={request.GET.get('from_class', '')}&to_class={to_class}&academic_year={academic_year_id}"

        if not student_ids:
            messages.error(
                request, "Please select at least one student to promote."
            )
            return redirect(redirect_url)

        if not to_class or not academic_year_id:
            messages.error(
                request, "Please select target class and academic year."
            )
            return redirect(redirect_url)

        # Convert to integers
        try:
            to_class_id = int(to_class)
            academic_year_id_int = int(academic_year_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid class or academic year selected.")
            return redirect(redirect_url)

        # Get students before update to save history
        students_to_promote = Student.objects.filter(
            id__in=student_ids, status="studying"
        )

        # Get the target class and academic year objects
        to_class_obj = ClassLevel.objects.get(id=to_class_id)
        to_year_obj = AcademicYear.objects.get(id=academic_year_id_int)

        # Save promotion history for each student
        for student in students_to_promote:
            StudentPromotionHistory.objects.create(
                student=student,
                from_class=student.class_level,
                to_class=to_class_obj,
                from_academic_year=student.academic_year,
                to_academic_year=to_year_obj,
                promoted_by=request.user,
            )

        promoted_count = students_to_promote.update(
            class_level_id=to_class_id, academic_year_id=academic_year_id_int
        )

        messages.success(
            request, f"{promoted_count} students promoted successfully!"
        )
        return redirect("students:list")

    context = {
        "classes": ClassLevel.objects.filter(is_active=True),
        "academic_years": AcademicYear.objects.filter(is_active=True),
        "students": students,
        "selected_class": int(selected_class) if selected_class else None,
        "selected_class_obj": ClassLevel.objects.get(id=selected_class)
        if selected_class
        else None,
        "selected_to_class": int(request.GET.get("to_class"))
        if request.GET.get("to_class")
        else None,
        "selected_academic_year": int(request.GET.get("academic_year"))
        if request.GET.get("academic_year")
        else None,
    }
    return render(request, "students/promote.html", context)


@login_required
@permission_required("students", "promote")
def get_student_promotion_history(request, student_id):
    """Get promotion history for a specific student (HTMX)."""
    student = get_object_or_404(Student, pk=student_id)
    history = (
        StudentPromotionHistory.objects.filter(student=student)
        .select_related(
            "from_class",
            "to_class",
            "from_academic_year",
            "to_academic_year",
            "promoted_by",
        )
        .order_by("-promoted_at")
    )

    html = render_to_string(
        "students/partials/promotion_history_row.html",
        {"history": history, "student": student},
    )
    return HttpResponse(html)


@login_required
@permission_required("students", "promote")
def promotion_history(request):
    """View promotion history."""
    from django.core.paginator import Paginator

    history = StudentPromotionHistory.objects.select_related(
        "student__user",
        "from_class",
        "to_class",
        "from_academic_year",
        "to_academic_year",
        "promoted_by",
    ).all()

    # Filter by student if provided
    student_id = request.GET.get("student")
    if student_id:
        history = history.filter(student_id=student_id)

    # Filter by from_class
    from_class_id = request.GET.get("from_class")
    if from_class_id:
        history = history.filter(from_class_id=from_class_id)

    # Filter by to_class
    to_class_id = request.GET.get("to_class")
    if to_class_id:
        history = history.filter(to_class_id=to_class_id)

    paginator = Paginator(history, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "history": page_obj,
        "classes": ClassLevel.objects.filter(is_active=True),
        "selected_student": student_id,
        "selected_from_class": int(from_class_id) if from_class_id else None,
        "selected_to_class": int(to_class_id) if to_class_id else None,
    }
    return render(request, "students/promote_history.html", context)
