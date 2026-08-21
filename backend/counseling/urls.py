from django.urls import path

from counseling.views import SessionCreateView, SessionMessageView

urlpatterns = [
    path("sessions/", SessionCreateView.as_view()),
    path("sessions/<uuid:session_id>/messages/", SessionMessageView.as_view()),
]
