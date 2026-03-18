from django import forms
from django_select2.forms import Select2Widget

from students.models import AcademicYear, ClassLevel, Student

from .models import FeeInvoice, FeePayment, FeeStructure, FeeType

INPUT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-4 py-2 text-sm "
    "focus:border-primary-500 focus:ring-2 focus:ring-primary-500 "
    "focus:ring-opacity-20"
)
CHECKBOX_CLASS = (
    "h-4 w-4 rounded border-gray-300 text-primary-600 "
    "focus:ring-primary-500"
)


class StudentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        class_name = obj.class_level.name if obj.class_level else "No Class"
        return f"{obj.get_full_name()} - {obj.admission_no} - {class_name}"


class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ["name", "category", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. Tuition Fee",
                }
            ),
            "category": forms.Select(attrs={"class": INPUT_CLASS}),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 4,
                    "placeholder": "Optional description for this fee type",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }


class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = [
            "class_level",
            "fee_type",
            "academic_year",
            "amount",
            "due_date",
            "late_fee",
            "is_active",
        ]
        widgets = {
            "class_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "fee_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "academic_year": forms.Select(attrs={"class": INPUT_CLASS}),
            "amount": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. 5000",
                    "step": "0.01",
                }
            ),
            "due_date": forms.DateInput(
                attrs={"class": INPUT_CLASS, "type": "date"}
            ),
            "late_fee": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. 50",
                    "step": "0.01",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_level"].queryset = ClassLevel.objects.filter(
            is_active=True
        ).order_by("numeric_name")
        self.fields["fee_type"].queryset = FeeType.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["academic_year"].queryset = AcademicYear.objects.filter(
            is_active=True
        ).order_by("-start_date")
        self.fields["class_level"].empty_label = "Select class"
        self.fields["fee_type"].empty_label = "Select fee type"
        self.fields["academic_year"].empty_label = "Select academic year"


class FeePaymentForm(forms.Form):
    payment_mode = forms.ChoiceField(
        choices=FeePayment.PAYMENT_MODE_CHOICES,
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "placeholder": "Optional payment note",
            }
        ),
    )


class AdminPaymentLookupForm(forms.Form):
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.none(),
        required=False,
        widget=Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select class",
            }
        ),
        empty_label="All classes",
    )
    student = StudentChoiceField(
        queryset=Student.objects.none(),
        widget=Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select student",
            }
        ),
        empty_label="Select student",
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.none(),
        widget=Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select fee structure",
            }
        ),
        empty_label="Select fee structure",
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(),
        widget=Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select academic year",
            }
        ),
        empty_label="Select academic year",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_level"].queryset = ClassLevel.objects.filter(
            is_active=True
        ).order_by("numeric_name")

        student_queryset = Student.objects.select_related(
            "user", "class_level"
        ).filter(status="studying", is_active=True).order_by(
            "class_level__numeric_name",
            "admission_no",
        )

        fee_structure_queryset = FeeStructure.objects.select_related(
            "class_level", "fee_type", "academic_year"
        ).filter(is_active=True, fee_type__is_active=True).order_by(
            "-academic_year__start_date",
            "class_level__numeric_name",
            "fee_type__name",
        )

        selected_class_level = None
        raw_class_level = (
            self.data.get(self.add_prefix("class_level"))
            if self.is_bound
            else self.initial.get("class_level")
        )
        if raw_class_level:
            try:
                selected_class_level = int(raw_class_level)
            except (TypeError, ValueError):
                selected_class_level = None

        if selected_class_level:
            student_queryset = student_queryset.filter(
                class_level_id=selected_class_level
            )
            fee_structure_queryset = fee_structure_queryset.filter(
                class_level_id=selected_class_level
            )

        self.fields["student"].queryset = student_queryset
        self.fields["fee_structure"].queryset = fee_structure_queryset
        self.fields["academic_year"].queryset = AcademicYear.objects.filter(
            is_active=True
        ).order_by("-start_date")

    def clean(self):
        cleaned_data = super().clean()
        class_level = cleaned_data.get("class_level")
        student = cleaned_data.get("student")
        fee_structure = cleaned_data.get("fee_structure")

        if class_level and student and student.class_level_id != class_level.id:
            self.add_error(
                "student",
                "Selected student does not belong to the chosen class.",
            )

        if (
            class_level
            and fee_structure
            and fee_structure.class_level_id != class_level.id
        ):
            self.add_error(
                "fee_structure",
                "Selected fee structure does not belong to the chosen class.",
            )

        return cleaned_data


class FeeInvoiceForm(forms.ModelForm):
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.none(),
        required=False,
        widget=Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select class",
            }
        ),
        empty_label="Select class",
    )

    class Meta:
        model = FeeInvoice
        fields = [
            "class_level",
            "student",
            "fee_structure",
            "academic_year",
            "total_amount",
            "paid_amount",
            "due_date",
            "status",
        ]
        widgets = {
            "student": Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select Student",
            }),
            "fee_structure": Select2Widget(attrs={"class": INPUT_CLASS}),
            "academic_year": Select2Widget(attrs={"class": INPUT_CLASS}),
            "total_amount": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "step": "1"}
            ),
            "paid_amount": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "step": "1"}
            ),
            "due_date": forms.DateInput(
                attrs={"class": INPUT_CLASS, "type": "date"}
            ),
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_level"].queryset = ClassLevel.objects.filter(
            is_active=True
        ).order_by("numeric_name")

        student_queryset = Student.objects.select_related(
            "user", "class_level"
        ).filter(status="studying", is_active=True).order_by(
            "class_level__numeric_name", "admission_no"
        )
        fee_structure_queryset = (
            FeeStructure.objects.select_related(
                "class_level", "fee_type", "academic_year"
            )
            .filter(is_active=True, fee_type__is_active=True)
            .order_by(
                "-academic_year__start_date",
                "class_level__numeric_name",
                "fee_type__name",
            )
        )

        selected_class_level = None
        raw_class_level = (
            self.data.get(self.add_prefix("class_level"))
            if self.is_bound
            else self.initial.get("class_level")
        )
        if not raw_class_level and self.instance.pk and self.instance.student_id:
            raw_class_level = self.instance.student.class_level_id

        if raw_class_level:
            try:
                selected_class_level = int(raw_class_level)
            except (TypeError, ValueError):
                selected_class_level = None

        if selected_class_level:
            self.initial.setdefault("class_level", selected_class_level)
            student_queryset = student_queryset.filter(
                class_level_id=selected_class_level
            )
            fee_structure_queryset = fee_structure_queryset.filter(
                class_level_id=selected_class_level
            )

        self.fields["student"] = StudentChoiceField(
            queryset=student_queryset,
            widget=Select2Widget(
                attrs={
                    "class": INPUT_CLASS,
                    "data-placeholder": "Select student",
                }
            ),
            empty_label="Select student",
            required=self.fields["student"].required,
        )
        self.fields["fee_structure"].widget = Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select fee structure",
            }
        )
        self.fields["academic_year"].widget = Select2Widget(
            attrs={
                "class": INPUT_CLASS,
                "data-placeholder": "Select academic year",
            }
        )
        self.fields["fee_structure"].queryset = fee_structure_queryset
        self.fields["academic_year"].queryset = AcademicYear.objects.filter(
            is_active=True
        ).order_by("-start_date")
        self.fields["fee_structure"].empty_label = "Select fee structure"
        self.fields["academic_year"].empty_label = "Select academic year"

    def clean(self):
        cleaned_data = super().clean()
        class_level = cleaned_data.get("class_level")
        student = cleaned_data.get("student")
        fee_structure = cleaned_data.get("fee_structure")

        if class_level and student and student.class_level_id != class_level.id:
            self.add_error(
                "student",
                "Selected student does not belong to the chosen class.",
            )

        if (
            class_level
            and fee_structure
            and fee_structure.class_level_id != class_level.id
        ):
            self.add_error(
                "fee_structure",
                "Selected fee structure does not belong to the chosen class.",
            )

        return cleaned_data
