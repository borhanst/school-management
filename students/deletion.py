def student_has_historical_records(student):
    checks = [
        student.attendances.exists(),
        student.leave_requests.exists(),
        student.grades.exists(),
        student.fee_invoices.exists(),
        student.transport_assignments.exists(),
        student.promotions.exists(),
    ]
    return any(checks)


def archive_student(student):
    student.is_active = False
    student.status = "left"
    student.save(update_fields=["is_active", "status", "updated_at"])

    student.user.is_active = False
    student.user.save(update_fields=["is_active"])


def delete_or_archive_student(student):
    if student_has_historical_records(student):
        archive_student(student)
        return "archived"

    student.user.delete()
    return "deleted"
