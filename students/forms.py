from django import forms

from accounts.models import ParentProfile, User

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
    parent_first_name = forms.CharField(max_length=150, required=False)
    parent_last_name = forms.CharField(max_length=150, required=False)
    parent_username = forms.CharField(max_length=150, required=False)
    parent_email = forms.EmailField(required=False)
    parent_password = forms.CharField(
        min_length=8, required=False, widget=forms.PasswordInput()
    )
    parent_phone = forms.CharField(max_length=20, required=False)
    parent_occupation = forms.CharField(max_length=100, required=False)
    parent_income = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    parent_relation = forms.ChoiceField(
        choices=ParentProfile.RELATION_CHOICES, required=False
    )
    parent_emergency_contact = forms.CharField(
        max_length=20, required=False
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already taken. Please choose another one."
            )
        return username

    def clean_parent_username(self):
        username = self.cleaned_data.get("parent_username", "").strip()
        if (
            username
            and User.objects.filter(username__iexact=username).exists()
        ):
            raise forms.ValidationError(
                "This parent username is already taken. Please choose another one."
            )
        return username

    def clean(self):
        cleaned_data = super().clean()
        class_level = cleaned_data.get("class_level")
        section = cleaned_data.get("section")
        academic_year = cleaned_data.get("academic_year")
        parent_fields = [
            "parent_first_name",
            "parent_last_name",
            "parent_username",
            "parent_email",
            "parent_password",
            "parent_phone",
            "parent_occupation",
            "parent_income",
            "parent_relation",
            "parent_emergency_contact",
        ]

        if section and class_level and section.class_level_id != class_level.id:
            self.add_error(
                "section", "Selected section does not belong to the class."
            )

        if (
            section
            and academic_year
            and section.academic_year_id != academic_year.id
        ):
            self.add_error(
                "section",
                "Selected section does not belong to the academic year.",
            )

        has_parent_data = any(
            cleaned_data.get(field) not in (None, "")
            for field in parent_fields
        )
        cleaned_data["has_parent_data"] = has_parent_data

        if has_parent_data:
            required_parent_fields = {
                "parent_first_name": "Parent first name is required.",
                "parent_last_name": "Parent last name is required.",
                "parent_username": "Parent username is required.",
                "parent_password": "Parent password is required.",
                "parent_relation": "Parent relation is required.",
            }
            for field, error_message in required_parent_fields.items():
                if not cleaned_data.get(field):
                    self.add_error(field, error_message)

        return cleaned_data
