from django.urls import path

from core.views import ComingSoonView

app_name = "communications"

urlpatterns = [
    path("", ComingSoonView.as_view(
        module_name="Communications",
        module_icon="fa-envelope",
        description="Communications module is under development. Soon you'll be able to send messages, notices, and announcements."
    ), name="index"),
    path(
        "messages/", ComingSoonView.as_view(
            module_name="Messages",
            module_icon="fa-envelope",
            description="Messaging system is under development. Soon you'll be able to send and receive messages within the system."
        ), name="messages"
    ),
    path("notices/", ComingSoonView.as_view(
        module_name="Notices",
        module_icon="fa-bullhorn",
        description="Notice board is under development. Soon you'll be able to publish and view important announcements."
    ), name="notices"),
]
