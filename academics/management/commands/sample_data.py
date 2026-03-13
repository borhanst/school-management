"""
Management command to create sample data for the school management system.
"""

from datetime import datetime, time

from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import Period, Subject, Timetable
from accounts.models import TeacherProfile, User
from students.models import AcademicYear, ClassLevel, Section, Student


class Command(BaseCommand):
    help = "Create sample data for the school management system"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample data...")

        # Create Academic Year
        academic_year, created = AcademicYear.objects.get_or_create(
            name="2025-2026",
            defaults={
                "start_date": timezone.make_aware(
                    timezone.datetime(2025, 1, 1)
                ),
                "end_date": timezone.make_aware(
                    timezone.datetime(2025, 12, 31)
                ),
                "is_current": True,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Academic Year: {academic_year.name}"
                )
            )
        else:
            self.stdout.write(
                f"Academic Year already exists: {academic_year.name}"
            )

        # Create Class Levels
        class_levels_data = [
            ("Grade 1", 1),
            ("Grade 2", 2),
            ("Grade 3", 3),
            ("Grade 4", 4),
            ("Grade 5", 5),
            ("Grade 6", 6),
            ("Grade 7", 7),
            ("Grade 8", 8),
            ("Grade 9", 9),
            ("Grade 10", 10),
        ]

        class_levels = {}
        for name, order in class_levels_data:
            level, created = ClassLevel.objects.get_or_create(
                name=name, defaults={"numeric_name": order}
            )
            class_levels[name] = level
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created Class Level: {name}")
                )

        # Create Sections and Subjects for Grade 6
        grade_6 = class_levels["Grade 6"]
        section_a, _ = Section.objects.get_or_create(
            name="A", class_level=grade_6, academic_year=academic_year
        )
        self.stdout.write(self.style.SUCCESS(f"Created Section: {section_a}"))

        # Create Subjects
        subjects_data = [
            ("Mathematics", "Math"),
            ("English", "Eng"),
            ("Science", "Sci"),
            ("History", "Hist"),
            ("Geography", "Geo"),
            ("Computer", "Comp"),
            ("Art", "Art"),
            ("Physical Education", "PE"),
        ]

        subjects = {}
        for name, code in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=name,
                defaults={"code": code, "class_level": grade_6},
            )
            subjects[name] = subject
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created Subject: {name}")
                )

        # Create Periods
        periods_data = [
            (1, time(8, 0), time(8, 40)),
            (2, time(8, 45), time(9, 25)),
            (3, time(9, 30), time(10, 10)),
            (4, time(10, 15), time(10, 55)),
            (5, time(11, 15), time(11, 55)),
            (6, time(12, 0), time(12, 40)),
            (7, time(13, 0), time(13, 40)),
            (8, time(13, 45), time(14, 25)),
        ]

        periods = {}
        for period_no, start, end in periods_data:
            period, created = Period.objects.get_or_create(
                period_no=period_no,
                defaults={"start_time": start, "end_time": end},
            )
            periods[period_no] = period
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created Period: {period_no}")
                )

        # Create Teacher User and Profile
        teacher_user, created = User.objects.get_or_create(
            username="teacher1",
            defaults={
                "first_name": "John",
                "last_name": "Smith",
                "email": "teacher1@school.com",
                "role": "teacher",
            },
        )
        if created:
            teacher_user.set_password("password123")
            teacher_user.save()

        teacher_profile, created = TeacherProfile.objects.get_or_create(
            user=teacher_user,
            defaults={"employee_id": "T001"},
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Teacher: {teacher_user.get_full_name()}"
                )
            )

        # Create another teacher
        teacher_user2, created = User.objects.get_or_create(
            username="teacher2",
            defaults={
                "first_name": "Sarah",
                "last_name": "Johnson",
                "email": "teacher2@school.com",
                "role": "teacher",
            },
        )
        if created:
            teacher_user2.set_password("password123")
            teacher_user2.save()

        teacher_profile2, created = TeacherProfile.objects.get_or_create(
            user=teacher_user2,
            defaults={"employee_id": "T002"},
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Teacher: {teacher_user2.get_full_name()}"
                )
            )

        # Create Student User and Profile
        student_user, created = User.objects.get_or_create(
            username="borhan",
            defaults={
                "first_name": "Alex",
                "last_name": "Brown",
                "email": "student1@school.com",
                "role": "student",
            },
        )
        if created:
            student_user.set_password("password123")
            student_user.save()

        student, created = Student.objects.get_or_create(
            user=student_user,
            defaults={
                "class_level": grade_6,
                "section": section_a,
                "roll_number": 1,
                "admission_date": timezone.now().date(),
                "status": "studying",
                "date_of_birth": datetime(2013, 5, 20),
                "academic_year": academic_year,
                "admission_no": "A001"
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Student: {student_user.get_full_name()}"
                )
            )

        # Create another student
        student_user2, created = User.objects.get_or_create(
            username="student2",
            defaults={
                "first_name": "Emma",
                "last_name": "Wilson",
                "email": "student2@school.com",
                "role": "student",
            },
        )
        if created:
            student_user2.set_password("password123")
            student_user2.save()

        student2, created = Student.objects.get_or_create(
            user=student_user2,
            defaults={
                "class_level": grade_6,
                "section": section_a,
                "roll_number": 2,
                "admission_date": timezone.now().date(),
                "status": "studying",
                "date_of_birth": datetime(2014, 5, 20),
                "academic_year": academic_year,
                "admission_no": "A002"
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Student: {student_user2.get_full_name()}"
                )
            )

        # Create Timetable for Grade 6 Section A
        timetable_data = [
            # Monday (0)
            (0, 1, "Mathematics", teacher_profile2),
            (0, 2, "English", teacher_profile),
            (0, 3, "Science", teacher_profile),
            (0, 4, "History", None),
            (0, 5, "Geography", None),
            (0, 6, "Computer", None),
            (0, 7, "Art", None),
            (0, 8, "Physical Education", None),
            # Tuesday (1)
            (1, 1, "English", teacher_profile),
            (1, 2, "Mathematics", teacher_profile2),
            (1, 3, "Science", teacher_profile),
            (1, 4, "Computer", None),
            (1, 5, "Geography", None),
            (1, 6, "History", None),
            (1, 7, "Art", None),
            (1, 8, "Physical Education", None),
            # Wednesday (2)
            (2, 1, "Mathematics", teacher_profile2),
            (2, 2, "English", teacher_profile),
            (2, 3, "History", None),
            (2, 4, "Geography", None),
            (2, 5, "Science", teacher_profile),
            (2, 6, "Computer", None),
            (2, 7, "Art", None),
            (2, 8, "Physical Education", None),
            # Thursday (3)
            (3, 1, "Science", teacher_profile),
            (3, 2, "Mathematics", teacher_profile2),
            (3, 3, "English", teacher_profile),
            (3, 4, "Computer", None),
            (3, 5, "Geography", None),
            (3, 6, "History", None),
            (3, 7, "Art", None),
            (3, 8, "Physical Education", None),
            # Friday (4)
            (4, 1, "Mathematics", teacher_profile2),
            (4, 2, "English", teacher_profile),
            (4, 3, "Science", teacher_profile),
            (4, 4, "History", None),
            (4, 5, "Geography", None),
            (4, 6, "Computer", None),
            (4, 7, "Art", None),
            (4, 8, "Physical Education", None),
        ]

        for day, period_no, subject_name, teacher in timetable_data:
            timetable, created = Timetable.objects.get_or_create(
                section=section_a,
                period=periods[period_no],
                day_of_week=day,
                academic_year=academic_year,
                defaults={
                    "subject": subjects[subject_name],
                    "teacher": teacher,
                    "room_no": f"Room {period_no}",
                },
            )
            if created:
                self.stdout.write(f"Created Timetable: {timetable}")

        self.stdout.write(
            self.style.SUCCESS("Sample data created successfully!")
        )
        self.stdout.write("")
        self.stdout.write("Login credentials:")
        self.stdout.write("  Admin: admin / password123")
        self.stdout.write("  Teacher: teacher1 / password123")
        self.stdout.write("  Student: student1 / password123")
