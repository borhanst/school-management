from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from dashboard.models import SystemSettings
from roles.decorators import PermissionRequiredMixin
from roles.services import assign_default_role_to_user

from .forms import (
    LoginForm,
    TeacherProfileForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import TeacherProfile, User


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(
                    request, f"Welcome back, {user.get_full_name()}!"
                )
                return redirect("dashboard:index")
        messages.error(request, "Invalid username or password")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect("dashboard:index")
    else:
        form = UserRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    """User profile view."""
    user = request.user
    teacher_profile = getattr(user, "teacher_profile", None)
    parent_profile = getattr(user, "parent_profile", None)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("accounts:profile")
    else:
        form = UserProfileForm(instance=user)

    context = {
        "form": form,
        "user": user,
        "teacher_profile": teacher_profile,
        "parent_profile": parent_profile,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def settings_view(request):
    """Admin-only system settings overview."""
    if not (request.user.is_superuser or request.user.role == "admin"):
        messages.error(
            request, "Only administrators can access the settings page."
        )
        return HttpResponseForbidden("Permission denied.")

    settings_queryset = SystemSettings.objects.order_by("category", "key")
    grouped_settings = []
    settings_by_category = {}

    for setting in settings_queryset:
        settings_by_category.setdefault(setting.category, []).append(setting)

    for category, items in settings_by_category.items():
        grouped_settings.append(
            {
                "name": category.replace("_", " ").title(),
                "items": items,
            }
        )

    context = {
        "grouped_settings": grouped_settings,
        "total_settings": settings_queryset.count(),
        "public_settings_count": settings_queryset.filter(
            is_public=True
        ).count(),
        "recent_settings": settings_queryset.order_by("-updated_at")[:5],
    }
    return render(request, "accounts/settings.html", context)


@method_decorator(login_required, name="dispatch")
class TeacherListView(PermissionRequiredMixin, ListView):
    """List all teachers."""

    model = TeacherProfile
    template_name = "accounts/teachers.html"
    context_object_name = "teachers"
    paginate_by = 20
    module_slug = "accounts"
    permission_codename = "view_users"

    def get_queryset(self):
        return TeacherProfile.objects.select_related("user").all()


@method_decorator(login_required, name="dispatch")
class TeacherCreateView(PermissionRequiredMixin, CreateView):
    """Create a new teacher."""

    model = TeacherProfile
    form_class = TeacherProfileForm
    template_name = "accounts/teacher_form.html"
    success_url = reverse_lazy("accounts:teachers")
    module_slug = "accounts"
    permission_codename = "add_user"

    def form_valid(self, form):
        # Create user for teacher
        username = self.request.POST.get("username")
        email = self.request.POST.get("email")
        password = self.request.POST.get("password")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role="teacher",
            first_name=self.request.POST.get("first_name"),
            last_name=self.request.POST.get("last_name"),
        )
        assign_default_role_to_user(user, assigned_by=self.request.user)

        teacher = user.teacher_profile
        for field, value in form.cleaned_data.items():
            setattr(teacher, field, value)
        teacher.save()

        messages.success(self.request, "Teacher created successfully!")
        return redirect(self.success_url)


@method_decorator(login_required, name="dispatch")
class TeacherDetailView(PermissionRequiredMixin, DetailView):
    """Teacher detail view."""

    model = TeacherProfile
    template_name = "accounts/teacher_detail.html"
    context_object_name = "teacher"
    module_slug = "accounts"
    permission_codename = "view_users"

    def get_queryset(self):
        return TeacherProfile.objects.select_related("user").prefetch_related(
            "subjects", "subject_assignments"
        )


@method_decorator(login_required, name="dispatch")
class TeacherUpdateView(PermissionRequiredMixin, UpdateView):
    """Update teacher view."""

    model = TeacherProfile
    form_class = TeacherProfileForm
    template_name = "accounts/teacher_form.html"
    success_url = reverse_lazy("accounts:teachers")
    module_slug = "accounts"
    permission_codename = "edit_user"
