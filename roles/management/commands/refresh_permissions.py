from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Refresh permission cache for all active users or specific user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            help="Refresh cache for specific user ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Refresh cache for all users (not just active)",
        )
        parser.add_argument(
            "--clear-only",
            action="store_true",
            help="Only clear cache without rebuilding",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        refresh_all = options.get("all")
        clear_only = options.get("clear_only")

        if user_id:
            # Refresh for specific user
            try:
                user = User.objects.get(id=user_id)
                user.clear_permission_cache()
                if not clear_only:
                    perms = user.get_all_permissions(force_refresh=True)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Refreshed permissions for user '{user.username}': "
                            f"{len(perms)} permissions"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Cleared cache for user '{user.username}'"
                        )
                    )
            except User.DoesNotExist:
                raise CommandError(f"User with ID {user_id} does not exist")

        elif refresh_all:
            # Refresh for all users
            users = User.objects.all()
            count = 0
            for user in users:
                user.clear_permission_cache()
                if not clear_only:
                    user.get_all_permissions(force_refresh=True)
                count += 1

            action = "Refreshed" if not clear_only else "Cleared"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} permissions cache for {count} users"
                )
            )

        else:
            # Default: refresh for active users only
            users = User.objects.filter(is_active=True)
            count = 0
            for user in users:
                user.clear_permission_cache()
                if not clear_only:
                    user.get_all_permissions(force_refresh=True)
                count += 1

            action = "Refreshed" if not clear_only else "Cleared"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} permissions cache for {count} active users"
                )
            )
