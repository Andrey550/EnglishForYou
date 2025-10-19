from django.urls import path
from . import views

urlpatterns = [
    path('board/', views.lessons_board_view, name='lessons_board'),
    path('generate/', views.generate_block_view, name='generate_block'),
    path('lesson/<int:lesson_id>/', views.lesson_detail_view, name='lesson_detail'),
    path('save-progress/', views.save_progress_view, name='save_progress'),
    path('complete-lesson/', views.complete_lesson_view, name='complete_lesson'),
]
