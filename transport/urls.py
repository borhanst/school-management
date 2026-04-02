from django.urls import path

from core.views import ComingSoonView

app_name = "transport"

urlpatterns = [
    path("", ComingSoonView.as_view(
        module_name="Transport",
        module_icon="fa-bus",
        description="Transport management module is under development. Soon you'll be able to manage routes, vehicles, and student transportation."
    ), name="index"),
    path("routes/", ComingSoonView.as_view(
        module_name="Transport",
        module_icon="fa-bus",
        description="Transport management module is under development. Soon you'll be able to manage routes, vehicles, and student transportation."
    ), name="routes"),
]
