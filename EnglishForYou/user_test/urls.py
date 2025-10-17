from django.urls import path
from . import views

app_name = 'user_test'

urlpatterns = [
    # Приветственная страница
    path('', views.test_intro_view, name='intro'),
    
    # Старт теста
    path('start/', views.start_test_view, name='start'),
    
    # Основная страница с вопросами
    path('question/', views.test_question_view, name='question'),
    
    # Завершение теста
    path('finish/', views.finish_test_view, name='finish'),
    
    # Таймаут (время истекло)
    path('timeout/', views.timeout_view, name='timeout'),
    
    # Результаты
    path('results/<int:session_id>/', views.test_results_view, name='results'),
]