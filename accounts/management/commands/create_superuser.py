from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

USERNAME = "admin"
EMAIL = "admin@school.com"
PHONE = "01000000000"
PASSWORD = "admin1234"


class Command(BaseCommand):
    help = "Create a superuser with hardcoded default values"

    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(username=USERNAME).exists():
            raise CommandError(f"User '{USERNAME}' already exists.")

        user = User.objects.create_superuser(
            username=USERNAME,
            email=EMAIL,
            password=PASSWORD,
            phone=PHONE,
            role="admin",
        )

        self.stdout.write(self.style.SUCCESS("Superuser created successfully!"))
        self.stdout.write(f"  Username : {user.username}")
        self.stdout.write(f"  Email    : {user.email}")
        self.stdout.write(f"  Phone    : {user.phone}")
        self.stdout.write(f"  Password : {PASSWORD}")
        self.stdout.write(f"  Role     : {user.role}")
        self.stdout.write(f"  Staff    : {user.is_staff}")
        self.stdout.write(f"  Superuser: {user.is_superuser}")
