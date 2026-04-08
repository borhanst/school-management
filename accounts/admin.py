from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ParentProfile, TeacherProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "get_full_name", "role", "is_active", "is_superuser")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("role", "phone", "address", "photo", "gender", "blood_group", "date_of_birth")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("role", "phone", "email")}),
    )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "designation", "is_class_teacher")
    search_fields = ("user__username", "user__first_name", "employee_id")
    list_filter = ("designation", "is_class_teacher")


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "relation", "occupation", "emergency_contact")
    search_fields = ("user__username", "user__first_name")
    list_filter = ("relation",)
