from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from roles.models import Module, PermissionType, Role, RolePermission

User = get_user_model()


class Command(BaseCommand):
    help = "Seed default modules, permissions, and roles"

    def handle(self, *args, **options):
        self.stdout.write("Seeding default modules and permissions...")

        # Default modules
        modules_data = [
            {
                "name": "Students",
                "slug": "students",
                "icon": "fa fa-users",
                "description": "Student management",
                "order": 1,
                "permissions": [
                    "view",
                    "add",
                    "edit",
                    "delete",
                    "promote",
                    "export",
                ],
            },
            {
                "name": "Academics",
                "slug": "academics",
                "icon": "fa fa-book",
                "description": "Academic management",
                "order": 2,
                "permissions": [
                    "view",
                    "add",
                    "edit",
                    "delete",
                    "manage_timetable",
                ],
            },
            {
                "name": "Attendance",
                "slug": "attendance",
                "icon": "fa fa-calendar-check",
                "description": "Attendance tracking",
                "order": 3,
                "permissions": [
                    "view",
                    "mark",
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
                "permissions": [
                    "view",
                    "add",
                    "edit",
                    "delete",
                    "publish_results",
                ],
            },
            {
                "name": "Fees",
                "slug": "fees",
                "icon": "fa fa-dollar-sign",
                "description": "Fee management",
                "order": 5,
                "permissions": [
                    "view",
                    "add",
                    "edit",
                    "delete",
                    "collect",
                    "export",
                ],
            },
            {
                "name": "Library",
                "slug": "library",
                "icon": "fa fa-book-open",
                "description": "Library management",
                "order": 6,
                "permissions": [
                    "view",
                    "add",
                    "edit",
                    "delete",
                    "issue",
                    "return",
                ],
            },
            {
                "name": "Transport",
                "slug": "transport",
                "icon": "fa fa-bus",
                "description": "Transport management",
                "order": 7,
                "permissions": ["view", "add", "edit", "delete", "track"],
            },
            {
                "name": "Communications",
                "slug": "communications",
                "icon": "fa fa-envelope",
                "description": "Notices and messages",
                "order": 8,
                "permissions": ["view", "add", "edit", "delete", "publish"],
            },
            {
                "name": "Reports",
                "slug": "reports",
                "icon": "fa fa-chart-bar",
                "description": "Report generation",
                "order": 9,
                "permissions": ["view", "generate", "export"],
            },
            {
                "name": "Dashboard",
                "slug": "dashboard",
                "icon": "fa fa-tachometer-alt",
                "description": "Dashboard access",
                "order": 10,
                "permissions": ["view", "view_analytics"],
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

        # Create modules and permissions
        created_modules = {}
        for module_data in modules_data:
            module, created = Module.objects.get_or_create(
                slug=module_data["slug"],
                defaults={
                    "name": module_data["name"],
                    "icon": module_data["icon"],
                    "description": module_data["description"],
                    "order": module_data["order"],
                },
            )
            created_modules[module.slug] = module

            if created:
                self.stdout.write(f"  Created module: {module.name}")

            # Create permission types
            for idx, perm_name in enumerate(module_data["permissions"]):
                perm_type, pt_created = PermissionType.objects.get_or_create(
                    module=module,
                    codename=perm_name,
                    defaults={
                        "name": perm_name.replace("_", " ").title(),
                        "order": idx,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(created_modules)} modules")
        )

        # Create default roles
        roles_data = [
            {
                "name": "Super Admin",
                "description": "Full system access",
                "priority": 100,
                "is_default": False,
                "permissions": "all",
            },
            {
                "name": "Administrator",
                "description": "Administrative access with some restrictions",
                "priority": 90,
                "is_default": False,
                "permissions": "admin",
            },
            {
                "name": "Teacher",
                "description": "Teacher access to academic features",
                "priority": 30,
                "is_default": False,
                "permissions": "teacher",
            },
            {
                "name": "Staff",
                "description": "General staff access",
                "priority": 20,
                "is_default": False,
                "permissions": "staff",
            },
            {
                "name": "Parent",
                "description": "Parent access to view child information",
                "priority": 10,
                "is_default": False,
                "permissions": "parent",
            },
            {
                "name": "Student",
                "description": "Student self-service access",
                "priority": 5,
                "is_default": False,
                "permissions": "student",
            },
        ]

        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data["name"],
                defaults={
                    "description": role_data["description"],
                    "priority": role_data["priority"],
                    "is_default": role_data["is_default"],
                },
            )

            if created:
                self.stdout.write(f"  Created role: {role.name}")

                # Assign permissions based on role type
                perm_type = role_data["permissions"]

                if perm_type == "all":
                    # Give all permissions
                    for module in Module.objects.all():
                        for pt in module.permission_types.all():
                            rp, _ = RolePermission.objects.get_or_create(
                                module=module, permission_type=pt
                            )
                            role.permissions.add(rp)

                elif perm_type == "admin":
                    # Admin gets most permissions except delete users
                    for module in Module.objects.all():
                        for pt in module.permission_types.all():
                            if not (
                                module.slug == "accounts"
                                and pt.codename == "delete_user"
                            ):
                                rp, _ = RolePermission.objects.get_or_create(
                                    module=module, permission_type=pt
                                )
                                role.permissions.add(rp)

                elif perm_type == "teacher":
                    # Teacher permissions
                    teacher_modules = [
                        "students",
                        "academics",
                        "attendance",
                        "examinations",
                        "dashboard",
                    ]
                    for module_slug in teacher_modules:
                        if module_slug in created_modules:
                            module = created_modules[module_slug]
                            for pt in module.permission_types.all():
                                if pt.codename in [
                                    "view",
                                    "add",
                                    "edit",
                                    "mark",
                                    "publish_results",
                                ]:
                                    rp, _ = (
                                        RolePermission.objects.get_or_create(
                                            module=module, permission_type=pt
                                        )
                                    )
                                    role.permissions.add(rp)

                elif perm_type == "staff":
                    # Staff permissions
                    staff_modules = ["students", "attendance", "fees"]
                    for module_slug in staff_modules:
                        if module_slug in created_modules:
                            module = created_modules[module_slug]
                            for pt in module.permission_types.all():
                                if pt.codename in ["view", "add"]:
                                    rp, _ = (
                                        RolePermission.objects.get_or_create(
                                            module=module, permission_type=pt
                                        )
                                    )
                                    role.permissions.add(rp)

                elif perm_type == "parent":
                    # Parent permissions (view only)
                    parent_modules = [
                        "students",
                        "attendance",
                        "fees",
                        "examinations",
                    ]
                    for module_slug in parent_modules:
                        if module_slug in created_modules:
                            module = created_modules[module_slug]
                            for pt in module.permission_types.all():
                                if pt.codename == "view":
                                    rp, _ = (
                                        RolePermission.objects.get_or_create(
                                            module=module, permission_type=pt
                                        )
                                    )
                                    role.permissions.add(rp)

                elif perm_type == "student":
                    # Student permissions (very limited)
                    student_modules = ["dashboard", "attendance"]
                    for module_slug in student_modules:
                        if module_slug in created_modules:
                            module = created_modules[module_slug]
                            for pt in module.permission_types.all():
                                if pt.codename == "view":
                                    rp, _ = (
                                        RolePermission.objects.get_or_create(
                                            module=module, permission_type=pt
                                        )
                                    )
                                    role.permissions.add(rp)

        self.stdout.write(
            self.style.SUCCESS("Successfully seeded roles and permissions!")
        )
        self.stdout.write("")
        self.stdout.write("Available URLs:")
        self.stdout.write("  - Modules: /roles/modules/")
        self.stdout.write("  - Roles: /roles/roles/")
        self.stdout.write("  - Assignments: /roles/assignments/")
