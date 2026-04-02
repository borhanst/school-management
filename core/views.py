from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View


@method_decorator(login_required, name="dispatch")
class ComingSoonView(View):
    """Generic coming soon page for modules under development."""

    module_name: str = ""
    module_icon: str = "fa-tools"
    description: str = "This feature is currently under development and will be available soon."

    def get(self, request, *args, **kwargs):
        context = {
            "module_name": self.module_name,
            "module_icon": self.module_icon,
            "description": self.description,
        }
        return render(request, "coming_soon.html", context)
