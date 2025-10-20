"""
Файл: apps.py
Описание: Конфигурация Django приложения lessons

Этот файл содержит базовые настройки приложения для системы уроков
английского языка. Приложение отвечает за:
- Создание и управление блоками уроков
- Генерацию контента с помощью AI
- Отслеживание прогресса пользователей
"""

from django.apps import AppConfig


class LessonsConfig(AppConfig):
    """
    Класс конфигурации приложения lessons
    
    Параметры:
    - default_auto_field: тип автоинкремента для ID (BigAutoField)
    - name: имя приложения в Django проекте
    """
    # Тип поля для автоматического ID (поддержка больших чисел)
    default_auto_field = 'django.db.models.BigAutoField'
    
    # Имя приложения
    name = 'lessons'
