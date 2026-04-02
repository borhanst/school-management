from .models import get_school_info, get_academic_setting, get_grading_setting


def global_settings(request):
    return {
        "school_info": get_school_info(),
        "academic_setting": get_academic_setting(),
        "grading_setting": get_grading_setting(),
    }
