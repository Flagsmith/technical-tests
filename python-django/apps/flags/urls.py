from django.urls import path

from apps.flags.views import get_flags

urlpatterns = [
    path("", get_flags),
]
