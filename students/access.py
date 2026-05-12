from students.models import AcademicYear


def get_current_academic_year():
    return (
        AcademicYear.objects.filter(is_current=True)
        .order_by("-start_date", "-id")
        .first()
    )
