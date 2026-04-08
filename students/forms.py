from django import forms

from accounts.models import User

from .models import AcademicYear, ClassLevel, Section


class StudentCreateForm(forms.Form):
    """Validate student account creation before saving."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    password = forms.CharField(min_length=8, widget=forms.PasswordInput())
    phone = forms.CharField(max_length=20, required=False)
    date_of_birth = forms.DateField()
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES)
    blood_group = forms.ChoiceField(
        choices=[("", "Select")] + User.BLOOD_GROUP_CHOICES,
        required=False,
    )
    religion = forms.ChoiceField(
        choices=[("", "Select")] + [
            ("islam", "Islam"),
            ("hinduism", "Hinduism"),
            ("christianity", "Christianity"),
            ("buddhism", "Buddhism"),
            ("other", "Other"),
        ],
        required=False,
    )
    aadhar_no = forms.CharField(max_length=20, required=False)
    admission_date = forms.DateField()
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.filter(is_active=True).order_by(
            "numeric_name"
        )
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True).select_related(
            "class_level"
        ),
        required=False,
    )
    roll_number = forms.IntegerField(required=False)
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.filter(is_active=True)
    )
    house = forms.CharField(max_length=50, required=False)
    previous_school = forms.CharField(max_length=200, required=False)
    tc_no = forms.CharField(max_length=50, required=False)

    # Parent/Guardian details (stored on Student model)
    father_name = forms.CharField(max_length=200, required=False)
    father_phone = forms.CharField(max_length=20, required=False)
    father_occupation = forms.CharField(max_length=100, required=False)
    mother_name = forms.CharField(max_length=200, required=False)
    mother_phone = forms.CharField(max_length=20, required=False)
    mother_occupation = forms.CharField(max_length=100, required=False)
    guardian_name = forms.CharField(max_length=200, required=False)
    guardian_phone = forms.CharField(max_length=20, required=False)
    guardian_relation = forms.CharField(max_length=50, required=False)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already taken. Please choose another one."
            )
        return username

    def clean(self):
        cleaned_data = super().clean()
        class_level = cleaned_data.get("class_level")
        section = cleaned_data.get("section")

        if section and class_level and section.class_level_id != class_level.id:
            self.add_error(
                "section", "Selected section does not belong to the class."
            )

        return cleaned_data


class StudentUpdateForm(forms.Form):
    """Validate student update before saving."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=20, required=False)
    date_of_birth = forms.DateField()
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES)
    blood_group = forms.ChoiceField(
        choices=[("", "Select")] + User.BLOOD_GROUP_CHOICES,
        required=False,
    )
    religion = forms.ChoiceField(
        choices=[("", "Select")] + [
            ("islam", "Islam"),
            ("hinduism", "Hinduism"),
            ("christianity", "Christianity"),
            ("buddhism", "Buddhism"),
            ("other", "Other"),
        ],
        required=False,
    )
    aadhar_no = forms.CharField(max_length=20, required=False)
    admission_date = forms.DateField()
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.filter(is_active=True).order_by(
            "numeric_name"
        )
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True).select_related(
            "class_level"
        ),
        required=False,
    )
    roll_number = forms.IntegerField(required=False)
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.filter(is_active=True)
    )
    house = forms.CharField(max_length=50, required=False)
    previous_school = forms.CharField(max_length=200, required=False)
    tc_no = forms.CharField(max_length=50, required=False)
    tc_date = forms.DateField(required=False)

    # Parent/Guardian details (stored on Student model)
    father_name = forms.CharField(max_length=200, required=False)
    father_phone = forms.CharField(max_length=20, required=False)
    father_occupation = forms.CharField(max_length=100, required=False)
    mother_name = forms.CharField(max_length=200, required=False)
    mother_phone = forms.CharField(max_length=20, required=False)
    mother_occupation = forms.CharField(max_length=100, required=False)
    guardian_name = forms.CharField(max_length=200, required=False)
    guardian_phone = forms.CharField(max_length=20, required=False)
    guardian_relation = forms.CharField(max_length=50, required=False)

    def clean(self):
        cleaned_data = super().clean()
        class_level = cleaned_data.get("class_level")
        section = cleaned_data.get("section")

        if section and class_level and section.class_level_id != class_level.id:
            self.add_error(
                "section", "Selected section does not belong to the class."
            )

        return cleaned_data
