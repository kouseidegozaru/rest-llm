from django.urls import path, include

urlpatterns = [
    path("api/", include("llm_api.urls")),
]
