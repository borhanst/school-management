from django.core.management.base import BaseCommand

from roles.models import Module, PermissionType
from roles.services import CORE_PERMISSION_TYPES


FIXED_MODULES = [
    {
        "name": "Students",
        "slug": "students",
        "icon": "fa fa-users",
        "description": "Student management",
        "order": 1,
        "permissions": ["promote", "export"],
    },
    {
        "name": "Academics",
        "slug": "academics",
        "icon": "fa fa-book",
        "description": "Academic management",
        "order": 2,
        "permissions": ["manage_timetable"],
    },
    {
        "name": "Attendance",
        "slug": "attendance",
        "icon": "fa fa-calendar-check",
        "description": "Attendance tracking",
        "order": 3,
        "permissions": [
            "mark",
            "apply_leave",
            "approve_leave",
            "view_reports",
        ],
    },
    {
        "name": "Examinations",
        "slug": "examinations",
        "icon": "fa fa-clipboard",
        "description": "Examination management",
        "order": 4,
        "permissions": ["publish_results"],
    },
    {
        "name": "Fees",
        "slug": "fees",
        "icon": "fa fa-dollar-sign",
        "description": "Fee management",
        "order": 5,
        "permissions": ["collect", "export", "manage_fee"],
    },
    {
        "name": "Library",
        "slug": "library",
        "icon": "fa fa-book-open",
        "description": "Library management",
        "order": 6,
        "permissions": ["issue", "return"],
    },
    {
        "name": "Transport",
        "slug": "transport",
        "icon": "fa fa-bus",
        "description": "Transport management",
        "order": 7,
        "permissions": ["track"],
    },
    {
        "name": "Communications",
        "slug": "communications",
        "icon": "fa fa-envelope",
        "description": "Notices and messages",
        "order": 8,
        "permissions": ["publish"],
    },
    {
        "name": "Reports",
        "slug": "reports",
        "icon": "fa fa-chart-bar",
        "description": "Report generation",
        "order": 9,
        "permissions": ["generate", "export"],
    },
    {
        "name": "Dashboard",
        "slug": "dashboard",
        "icon": "fa fa-tachometer-alt",
        "description": "Dashboard access",
        "order": 10,
        "permissions": ["view_analytics"],
    },
    {
        "name": "Accounts",
        "slug": "accounts",
        "icon": "fa fa-user-cog",
        "description": "User account management",
        "order": 11,
        "permissions": [
            "view_users",
            "add_user",
            "edit_user",
            "delete_user",
            "manage_roles",
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Create the fixed predefined modules. Existing modules are skipped."
    )

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        self.stdout.write("Creating fixed modules...")

        for module_data in FIXED_MODULES:
            module, created = Module.objects.get_or_create(
                slug=module_data["slug"],
                defaults={
                    "name": module_data["name"],
                    "icon": module_data["icon"],
                    "description": module_data["description"],
                    "order": module_data["order"],
                    "is_active": True,
                },
            )

            for index, (permission_code, label) in enumerate(
                CORE_PERMISSION_TYPES
            ):
                PermissionType.objects.get_or_create(
                    module=module,
                    codename=permission_code,
                    defaults={
                        "name": label,
                        "order": index,
                    },
                )

            for index, permission_code in enumerate(
                module_data["permissions"], start=len(CORE_PERMISSION_TYPES)
            ):
                PermissionType.objects.get_or_create(
                    module=module,
                    codename=permission_code,
                    defaults={
                        "name": permission_code.replace("_", " ").title(),
                        "order": index,
                    },
                )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created module: {module.slug}")
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Synced permissions for existing module: {module.slug}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Created {created_count}, skipped {skipped_count}."
            )
        )
