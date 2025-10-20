"""
Файл: urls.py
Описание: URL маршруты для приложения lessons

Этот файл определяет все URL-адреса для работы с уроками:
- board/ - доска с блоками уроков пользователя
- generate/ - генерация нового блока с помощью AI
- lesson/<id>/ - детальная страница урока с упражнениями
- save-progress/ - AJAX endpoint для сохранения прогресса
- complete-lesson/ - AJAX endpoint для завершения урока
"""

from django.urls import path
from . import views

# Маршруты приложения lessons
urlpatterns = [
    # Главная доска с блоками уроков
    path('board/', views.lessons_board_view, name='lessons_board'),
    
    # Генерация нового блока через AI
    path('generate/', views.generate_block_view, name='generate_block'),
    
    # Детальная страница урока
    path('lesson/<int:lesson_id>/', views.lesson_detail_view, name='lesson_detail'),
    
    # AJAX: Сохранение прогресса по упражнениям
    path('save-progress/', views.save_progress_view, name='save_progress'),
    
    # AJAX: Завершение урока
    path('complete-lesson/', views.complete_lesson_view, name='complete_lesson'),
]
