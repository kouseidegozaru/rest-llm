from django.urls import path
from .views import ChatView, ChatStreamView, ModelListView, HealthView

urlpatterns = [
    path("chat/",        ChatView.as_view(),        name="chat"),
    path("chat/stream/", ChatStreamView.as_view(),  name="chat-stream"),
    path("models/",      ModelListView.as_view(),   name="models"),
    path("health/",      HealthView.as_view(),       name="health"),
]
