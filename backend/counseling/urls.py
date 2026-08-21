from django.urls import path

from counseling.views import (
    AdminSessionDetailView,
    AdminUserDeleteView,
    AdminUserListView,
    AdminUserSessionsView,
    AuthLoginView,
    AuthRegisterView,
    SessionCreateView,
    SessionMessageView,
)

urlpatterns = [
    path("auth/register/", AuthRegisterView.as_view()),
    path("auth/login/", AuthLoginView.as_view()),
    path("sessions/", SessionCreateView.as_view()),
    path("sessions/<uuid:session_id>/messages/", SessionMessageView.as_view()),
    path("admin/users/", AdminUserListView.as_view()),
    path("admin/users/<str:user_id>/", AdminUserDeleteView.as_view()),
    path("admin/users/<str:user_id>/sessions/", AdminUserSessionsView.as_view()),
    path("admin/sessions/<uuid:session_id>/messages/", AdminSessionDetailView.as_view()),
]
