from django.urls import path

from transport import views

app_name = "transport"

urlpatterns = [
    path("", views.transport_index, name="index"),
    path("routes/", views.route_list, name="routes"),
]
