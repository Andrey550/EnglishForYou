"""
Конфигурация приложения user_test.

Этот файл содержит настройки Django-приложения для тестирования уровня английского языка.
Используется Django для автоматической регистрации приложения в проекте.
"""

from django.apps import AppConfig


class UserTestConfig(AppConfig):
    """
    Класс конфигурации приложения тестирования.
    
    Параметры:
        default_auto_field: Тип поля для автоматических первичных ключей (BigAutoField)
        name: Название приложения в Django проекте
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_test'
