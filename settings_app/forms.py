from django import forms
from .models import (
    SchoolInfo, AcademicSetting, GradingSetting, GradeScale,
    AttendanceSetting, ExaminationSetting, ExamTypeConfig,
    PromotionSetting, StudentSetting, FeeSetting,
    LibrarySetting, TransportSetting, ReportCardSetting,
)
from students.models import AcademicYear


class SchoolInfoForm(forms.ModelForm):
    class Meta:
        model = SchoolInfo
        fields = "__all__"
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class AcademicYearForm(forms.ModelForm):
    """Form for creating/editing academic years."""
    class Meta:
        model = AcademicYear
        fields = ["name", "start_date", "end_date", "is_current", "is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class AcademicSettingForm(forms.ModelForm):
    class Meta:
        model = AcademicSetting
        fields = "__all__"
        widgets = {
            "working_days": forms.CheckboxSelectMultiple(
                choices=[
                    (0, "Sunday"), (1, "Monday"), (2, "Tuesday"),
                    (3, "Wednesday"), (4, "Thursday"), (5, "Friday"), (6, "Saturday"),
                ]
            ),
        }


class GradingSettingForm(forms.ModelForm):
    class Meta:
        model = GradingSetting
        fields = "__all__"


class GradeScaleForm(forms.ModelForm):
    class Meta:
        model = GradeScale
        fields = "__all__"


class AttendanceSettingForm(forms.ModelForm):
    class Meta:
        model = AttendanceSetting
        fields = "__all__"


class ExaminationSettingForm(forms.ModelForm):
    class Meta:
        model = ExaminationSetting
        fields = "__all__"


class ExamTypeConfigForm(forms.ModelForm):
    class Meta:
        model = ExamTypeConfig
        fields = "__all__"


class PromotionSettingForm(forms.ModelForm):
    class Meta:
        model = PromotionSetting
        fields = "__all__"


class StudentSettingForm(forms.ModelForm):
    class Meta:
        model = StudentSetting
        fields = "__all__"


class FeeSettingForm(forms.ModelForm):
    class Meta:
        model = FeeSetting
        fields = "__all__"


class LibrarySettingForm(forms.ModelForm):
    class Meta:
        model = LibrarySetting
        fields = "__all__"


class TransportSettingForm(forms.ModelForm):
    class Meta:
        model = TransportSetting
        fields = "__all__"


class ReportCardSettingForm(forms.ModelForm):
    class Meta:
        model = ReportCardSetting
        fields = "__all__"
