from django.urls import path
from . import views


urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_token_view, name="verify_token"),
    path("me/", views.me_view, name="me"),
]
