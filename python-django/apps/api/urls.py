from django.urls import path, include

urlpatterns = [path("flags/", include("apps.flags.urls"))]
