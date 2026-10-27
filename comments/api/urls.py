from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("commenting/", include("commenting.api.urls", namespace="commenting")),
]
