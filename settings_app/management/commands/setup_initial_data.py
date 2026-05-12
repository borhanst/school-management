from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Setup initial data for the full School Management System"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-superuser",
            action="store_true",
            help="Skip creating superuser",
        )
        parser.add_argument(
            "--skip-sample-data",
            action="store_true",
            help="Skip creating sample data",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting full system setup..."))

        self._run_step(1, 5, "Creating fixed modules", "create_fixed_modules")
        self._run_step(2, 5, "Seeding roles and permissions", "seed_roles")

        if not options["skip_superuser"]:
            try:
                self._run_step(3, 5, "Creating superuser", "create_superuser")
            except Exception as exc:
                if "already exists" in str(exc):
                    self.stdout.write(
                        self.style.WARNING("Superuser already exists, skipping...")
                    )
                else:
                    raise
        else:
            self.stdout.write("\nStep 3/5: Skipping superuser creation...")

        self._run_step(4, 5, "Seeding default settings", "seed_default_settings")

        if not options["skip_sample_data"]:
            self._run_step(5, 5, "Creating sample data", "sample_data")
        else:
            self.stdout.write("\nStep 5/5: Skipping sample data creation...")

        self.stdout.write(
            self.style.SUCCESS("\nFull system setup completed successfully!")
        )

    def _run_step(self, step_number, total_steps, label, command_name):
        self.stdout.write(f"\nStep {step_number}/{total_steps}: {label}...")
        try:
            call_command(command_name)
            self.stdout.write(self.style.SUCCESS(f"Done: {label}"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Failed: {label} - {exc}"))
            raise
