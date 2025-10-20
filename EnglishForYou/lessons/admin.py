"""
Файл: admin.py
Описание: Настройка административной панели Django для управления уроками

Этот файл содержит конфигурацию административного интерфейса для моделей:
- LessonBlock: блоки уроков с фильтрацией по уровню и статусу
- Lesson: отдельные уроки с сортировкой по типу
- LessonProgress: прогресс пользователей по урокам
"""

from django.contrib import admin
from .models import LessonBlock, Lesson, LessonProgress


@admin.register(LessonBlock)
class LessonBlockAdmin(admin.ModelAdmin):
    """
    Административная панель для управления блоками уроков
    
    Функции:
    - Просмотр списка блоков с основными характеристиками
    - Фильтрация по уровню сложности и статусу завершения
    - Поиск по названию, пользователю и грамматической теме
    """
    # Поля для отображения в списке
    list_display = ['id', 'user', 'order', 'title', 'level', 'difficulty_level', 'is_completed', 'is_passed', 'completion_percent', 'created_at']
    
    # Фильтры в боковой панели
    list_filter = ['level', 'difficulty_level', 'is_completed', 'is_passed']
    
    # Поля для поиска
    search_fields = ['title', 'user__username', 'grammar_topic']
    
    # Сортировка по умолчанию
    ordering = ['user', 'order']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """
    Административная панель для управления отдельными уроками
    
    Функции:
    - Просмотр уроков внутри блоков
    - Фильтрация по типу урока (грамматика, лексика, чтение)
    - Управление статусом разблокировки урока
    """
    # Поля для отображения в списке
    list_display = ['id', 'block', 'order', 'lesson_type', 'title', 'is_unlocked', 'estimated_time']
    
    # Фильтры в боковой панели
    list_filter = ['lesson_type', 'is_unlocked']
    
    # Поля для поиска
    search_fields = ['title', 'block__title']
    
    # Сортировка по умолчанию
    ordering = ['block', 'order']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    """
    Административная панель для просмотра прогресса пользователей
    
    Функции:
    - Просмотр результатов пользователей по урокам
    - Фильтрация по статусу завершения и типу урока
    - Отслеживание количества попыток и последнего доступа
    """
    # Поля для отображения в списке
    list_display = ['id', 'user', 'lesson', 'best_score', 'current_score', 'is_completed', 'attempts', 'last_accessed']
    
    # Фильтры в боковой панели
    list_filter = ['is_completed', 'lesson__lesson_type']
    
    # Поля для поиска
    search_fields = ['user__username', 'lesson__title']
    
    # Сортировка по умолчанию (сначала последние)
    ordering = ['-last_accessed']
