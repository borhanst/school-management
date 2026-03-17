from django import forms

from accounts.models import TeacherProfile
from students.models import AcademicYear, ClassLevel, Section

from .models import Period, Subject, Timetable


INPUT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-4 py-2 text-sm "
    "focus:border-primary-500 focus:ring-2 focus:ring-primary-500 "
    "focus:ring-opacity-20"
)
CHECKBOX_CLASS = "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"


class ClassLevelForm(forms.ModelForm):
    class Meta:
        model = ClassLevel
        fields = [
            "name",
            "numeric_name",
            "stream",
            "capacity",
            "description",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. Class 6"}
            ),
            "numeric_name": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. 6"}
            ),
            "stream": forms.Select(attrs={"class": INPUT_CLASS}),
            "capacity": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. 40"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 4,
                    "placeholder": "Optional notes about this class",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            "name",
            "code",
            "subject_type",
            "class_level",
            "teacher",
            "credit_hours",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. Mathematics"}
            ),
            "code": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. MATH-101"}
            ),
            "subject_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "class_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "teacher": forms.Select(attrs={"class": INPUT_CLASS}),
            "credit_hours": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. 4"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_level"].queryset = ClassLevel.objects.filter(
            is_active=True
        ).order_by("numeric_name")
        self.fields["teacher"].queryset = TeacherProfile.objects.select_related(
            "user"
        ).order_by("user__first_name", "user__last_name", "employee_id")
        self.fields["teacher"].empty_label = "Select teacher"
        self.fields["class_level"].empty_label = "Select class"


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = [
            "class_level",
            "name",
            "academic_year",
            "capacity",
            "room_no",
            "is_active",
        ]
        widgets = {
            "class_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. A"}
            ),
            "academic_year": forms.Select(attrs={"class": INPUT_CLASS}),
            "capacity": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. 40"}
            ),
            "room_no": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. Room 101"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_level"].queryset = ClassLevel.objects.filter(
            is_active=True
        ).order_by("numeric_name")
        self.fields["academic_year"].queryset = AcademicYear.objects.filter(
            is_active=True
        ).order_by("-start_date")
        self.fields["class_level"].empty_label = "Select class"
        self.fields["academic_year"].empty_label = "Select academic year"


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = [
            "section",
            "period",
            "subject",
            "teacher",
            "day_of_week",
            "room_no",
        ]
        widgets = {
            "section": forms.Select(attrs={"class": INPUT_CLASS}),
            "period": forms.Select(attrs={"class": INPUT_CLASS}),
            "subject": forms.Select(attrs={"class": INPUT_CLASS}),
            "teacher": forms.Select(attrs={"class": INPUT_CLASS}),
            "day_of_week": forms.Select(attrs={"class": INPUT_CLASS}),
            "room_no": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. Room 203"}
            ),
        }

    def __init__(self, *args, **kwargs):
        academic_year = kwargs.pop("academic_year", None)
        self.academic_year = academic_year
        super().__init__(*args, **kwargs)
        self.fields["period"].queryset = Period.objects.order_by("period_no")
        self.fields["teacher"].queryset = TeacherProfile.objects.select_related(
            "user"
        ).order_by("user__first_name", "user__last_name", "employee_id")
        self.fields["subject"].queryset = Subject.objects.select_related(
            "class_level"
        ).filter(is_active=True).order_by("class_level__numeric_name", "name")

        sections = Section.objects.select_related("class_level").filter(
            is_active=True
        )
        if academic_year is not None:
            sections = sections.filter(academic_year=academic_year)
        self.fields["section"].queryset = sections.order_by(
            "class_level__numeric_name", "name"
        )
        self.fields["section"].empty_label = "Select section"
        self.fields["period"].empty_label = "Select period"
        self.fields["subject"].empty_label = "Select subject"
        self.fields["teacher"].empty_label = "Select teacher"

    def clean(self):
        cleaned_data = super().clean()
        section = cleaned_data.get("section")
        period = cleaned_data.get("period")
        day_of_week = cleaned_data.get("day_of_week")
        subject = cleaned_data.get("subject")
        academic_year = self.academic_year or getattr(
            self.instance, "academic_year", None
        )

        if section and subject and subject.class_level_id != section.class_level_id:
            self.add_error(
                "subject",
                "Selected subject does not belong to the section's class.",
            )

        if section and period and day_of_week is not None and academic_year:
            duplicate_qs = Timetable.objects.filter(
                section=section,
                period=period,
                day_of_week=day_of_week,
                academic_year=academic_year,
            )
            if self.instance.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)

            if duplicate_qs.exists():
                raise forms.ValidationError(
                    "A timetable entry already exists for this section, period, day, and academic year."
                )

        return cleaned_data
