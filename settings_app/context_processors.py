from .models import (
    get_school_info,
    get_academic_setting,
    get_grading_setting,
    get_attendance_setting,
    get_examination_setting,
    get_promotion_setting,
    get_student_setting,
    get_fee_setting,
    get_library_setting,
    get_transport_setting,
    get_report_card_setting,
)


def global_settings(request):
    return {
        "school_info": get_school_info(),
        "academic_setting": get_academic_setting(),
        "grading_setting": get_grading_setting(),
        "attendance_setting": get_attendance_setting(),
        "examination_setting": get_examination_setting(),
        "promotion_setting": get_promotion_setting(),
        "student_setting": get_student_setting(),
        "fee_setting": get_fee_setting(),
        "library_setting": get_library_setting(),
        "transport_setting": get_transport_setting(),
        "report_card_setting": get_report_card_setting(),
    }
