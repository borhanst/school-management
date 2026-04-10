from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from students.models import AcademicYear
from .models import (
    get_school_info, get_academic_setting, get_grading_setting,
    get_attendance_setting, get_examination_setting, get_promotion_setting,
    get_student_setting, get_fee_setting, get_library_setting,
    get_transport_setting, get_report_card_setting,
    GradeScale, ExamTypeConfig,
)
from .forms import (
    SchoolInfoForm, AcademicSettingForm, GradingSettingForm, GradeScaleForm,
    AttendanceSettingForm, ExaminationSettingForm, ExamTypeConfigForm,
    PromotionSettingForm, StudentSettingForm, FeeSettingForm,
    LibrarySettingForm, TransportSettingForm, ReportCardSettingForm,
    AcademicYearForm,
)


@login_required
def settings_index(request):
    return render(request, "settings/index.html")


# Academic Year Management Views
@login_required
def academic_year_list(request):
    """List all academic years."""
    years = AcademicYear.objects.all().order_by("-start_date")
    context = {"years": years}
    return render(request, "settings/academic_year_list.html", context)


@login_required
def academic_year_create(request):
    """Create a new academic year."""
    if request.method == "POST":
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic year created successfully.")
            return redirect("settings:academic-year-list")
    else:
        form = AcademicYearForm()
    return render(request, "settings/academic_year_form.html", {"form": form, "title": "Create Academic Year"})


@login_required
def academic_year_edit(request, pk):
    """Edit an academic year."""
    year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == "POST":
        form = AcademicYearForm(request.POST, instance=year)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic year updated successfully.")
            return redirect("settings:academic-year-list")
    else:
        form = AcademicYearForm(instance=year)
    return render(request, "settings/academic_year_form.html", {"form": form, "title": "Edit Academic Year", "year": year})


@login_required
@require_POST
def academic_year_delete(request, pk):
    """Delete an academic year."""
    year = get_object_or_404(AcademicYear, pk=pk)
    
    # Prevent deleting if it's the current year
    if year.is_current:
        messages.error(request, "Cannot delete the current academic year.")
        return redirect("settings:academic-year-list")
    
    # Check if there are related records
    if (year.students.exists() or 
        year.question_banks.exists() or 
        year.fee_structures.exists() or
        year.sections.exists()):
        messages.error(
            request, 
            f"Cannot delete '{year.name}' because it has related records (students, question banks, fee structures, or sections)."
        )
        return redirect("settings:academic-year-list")
    
    year.delete()
    messages.success(request, f"Academic year '{year.name}' deleted successfully.")
    return redirect("settings:academic-year-list")


@login_required
def school_info_settings(request):
    obj = get_school_info()
    if request.method == "POST":
        form = SchoolInfoForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "School information saved successfully.")
            return redirect("settings:school-info")
    else:
        form = SchoolInfoForm(instance=obj)
    return render(request, "settings/school_info.html", {"form": form})


@login_required
def academic_settings(request):
    obj = get_academic_setting()
    if request.method == "POST":
        form = AcademicSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic settings saved successfully.")
            return redirect("settings:academic")
    else:
        form = AcademicSettingForm(instance=obj)
    return render(request, "settings/academic.html", {"form": form})


@login_required
def grading_settings(request):
    obj = get_grading_setting()
    if request.method == "POST":
        form = GradingSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Grading settings saved successfully.")
            return redirect("settings:grading")
    else:
        form = GradingSettingForm(instance=obj)
    grade_scales = obj.grade_scales.all()
    return render(request, "settings/grading.html", {"form": form, "grade_scales": grade_scales})


@login_required
def attendance_settings(request):
    obj = get_attendance_setting()
    if request.method == "POST":
        form = AttendanceSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Attendance settings saved successfully.")
            return redirect("settings:attendance")
    else:
        form = AttendanceSettingForm(instance=obj)
    return render(request, "settings/attendance.html", {"form": form})


@login_required
def examination_settings(request):
    obj = get_examination_setting()
    if request.method == "POST":
        form = ExaminationSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Examination settings saved successfully.")
            return redirect("settings:examination")
    else:
        form = ExaminationSettingForm(instance=obj)
    exam_types = ExamTypeConfig.objects.all()
    return render(request, "settings/examination.html", {"form": form, "exam_types": exam_types})


@login_required
def promotion_settings(request):
    obj = get_promotion_setting()
    if request.method == "POST":
        form = PromotionSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Promotion settings saved successfully.")
            return redirect("settings:promotion")
    else:
        form = PromotionSettingForm(instance=obj)
    return render(request, "settings/promotion.html", {"form": form})


@login_required
def student_settings(request):
    obj = get_student_setting()
    if request.method == "POST":
        form = StudentSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Student settings saved successfully.")
            return redirect("settings:student")
    else:
        form = StudentSettingForm(instance=obj)
    return render(request, "settings/student.html", {"form": form})


@login_required
def fee_settings(request):
    obj = get_fee_setting()
    if request.method == "POST":
        form = FeeSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee settings saved successfully.")
            return redirect("settings:fee")
    else:
        form = FeeSettingForm(instance=obj)
    return render(request, "settings/fee.html", {"form": form})


@login_required
def library_settings(request):
    obj = get_library_setting()
    if request.method == "POST":
        form = LibrarySettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Library settings saved successfully.")
            return redirect("settings:library")
    else:
        form = LibrarySettingForm(instance=obj)
    return render(request, "settings/library.html", {"form": form})


@login_required
def transport_settings(request):
    obj = get_transport_setting()
    if request.method == "POST":
        form = TransportSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Transport settings saved successfully.")
            return redirect("settings:transport")
    else:
        form = TransportSettingForm(instance=obj)
    return render(request, "settings/transport.html", {"form": form})


@login_required
def report_card_settings(request):
    obj = get_report_card_setting()
    if request.method == "POST":
        form = ReportCardSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Report card settings saved successfully.")
            return redirect("settings:report-card")
    else:
        form = ReportCardSettingForm(instance=obj)
    return render(request, "settings/report_card.html", {"form": form})
