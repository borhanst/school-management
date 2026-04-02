from django import template

register = template.Library()


@register.simple_tag
def get_setting(name):
    """Get a setting value by name."""
    from settings_app.models import (
        get_school_info, get_academic_setting, get_grading_setting,
        get_attendance_setting, get_examination_setting, get_promotion_setting,
        get_student_setting, get_fee_setting, get_library_setting,
        get_transport_setting, get_report_card_setting,
    )
    getters = {
        "school_info": get_school_info,
        "academic": get_academic_setting,
        "grading": get_grading_setting,
        "attendance": get_attendance_setting,
        "examination": get_examination_setting,
        "promotion": get_promotion_setting,
        "student": get_student_setting,
        "fee": get_fee_setting,
        "library": get_library_setting,
        "transport": get_transport_setting,
        "report_card": get_report_card_setting,
    }
    getter = getters.get(name)
    if getter:
        return getter()
    return None
