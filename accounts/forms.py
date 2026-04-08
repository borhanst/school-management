from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from roles.services import assign_default_role_to_user

from .models import ParentProfile, TeacherProfile, User


FIELD_CSS = "w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
PASSWORD_CSS = "w-full pl-10 pr-10 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"


class LoginForm(AuthenticationForm):
    """Login with email or phone number."""

    username = forms.CharField(
        label="Email or Phone",
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CSS,
                "placeholder": "Email or Phone Number",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": PASSWORD_CSS,
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        )
    )

    def clean_username(self):
        value = self.cleaned_data.get("username", "").strip()
        if not value:
            return value
        if "@" in value:
            user = User.objects.filter(email__iexact=value).first()
        else:
            user = User.objects.filter(phone=value).first()
        if user:
            return user.username
        raise forms.ValidationError("No account found with that email or phone number.")


class UserRegistrationForm(UserCreationForm):
    """User registration form for parents only."""

    phone = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CSS,
                "placeholder": "Phone Number",
                "autocomplete": "tel",
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": FIELD_CSS,
                "placeholder": "Email Address",
                "autocomplete": "email",
            }
        )
    )
    first_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CSS,
                "placeholder": "First Name",
            }
        )
    )
    last_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CSS,
                "placeholder": "Last Name",
            }
        )
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": PASSWORD_CSS,
                "placeholder": "Password",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": PASSWORD_CSS,
                "placeholder": "Confirm Password",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("phone", "email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone") or None
        if phone and User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone

    def _generate_username(self, email):
        base = email.split("@")[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self._generate_username(self.cleaned_data["email"])
        user.email = self.cleaned_data["email"]
        user.role = "parent"
        user.phone = self.cleaned_data.get("phone") or None
        if commit:
            user.save()
            assign_default_role_to_user(user)
        return user


class UserProfileForm(forms.ModelForm):
    """User profile form."""

    def clean_phone(self):
        return self.cleaned_data.get("phone") or None
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "photo",
            "gender",
            "blood_group",
            "date_of_birth",
        )
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500",
                    "rows": 3,
                }
            ),
            "photo": forms.FileInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg"
                }
            ),
            "gender": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "blood_group": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "date_of_birth": forms.DateInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500",
                    "type": "date",
                }
            ),
        }


class TeacherProfileForm(forms.ModelForm):
    """Teacher profile form."""

    class Meta:
        model = TeacherProfile
        fields = (
            "employee_id",
            "designation",
            "qualification",
            "experience",
            "joining_date",
            "specializations",
        )
        widgets = {
            "employee_id": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "designation": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "qualification": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500",
                    "rows": 3,
                }
            ),
            "experience": forms.NumberInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "joining_date": forms.DateInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500",
                    "type": "date",
                }
            ),
            "specializations": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500",
                    "rows": 2,
                }
            ),
        }


class ParentProfileForm(forms.ModelForm):
    """Parent profile form."""

    class Meta:
        model = ParentProfile
        fields = ("occupation", "income", "relation", "emergency_contact")
        widgets = {
            "occupation": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "income": forms.NumberInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "relation": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
            "emergency_contact": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                }
            ),
        }
