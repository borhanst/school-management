from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("roles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="default_for_role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "No default user type"),
                    ("admin", "Administrator"),
                    ("teacher", "Teacher"),
                    ("student", "Student"),
                    ("parent", "Parent"),
                ],
                default="",
                help_text="Automatically assign this role to new users of the selected type.",
                max_length=20,
            ),
        ),
    ]
