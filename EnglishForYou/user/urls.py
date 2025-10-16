from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register_view, name='register'),
    path('login', views.login_view, name='login'),
    path('user_profile', views.user_profile_view, name='user_profile'),
    path('logout', views.logout_view, name='logout'),
]
