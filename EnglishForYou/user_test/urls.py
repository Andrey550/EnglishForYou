from django.urls import path
from . import views

urlpatterns = [
    path('user_test_intro', views.user_test_intro_view, name='user_test_intro'),
]
