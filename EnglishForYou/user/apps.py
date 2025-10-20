"""apps.py - Конфигурация приложения user.

Этот файл содержит настройки Django-приложения для работы с пользователями.
"""

from django.apps import AppConfig


# Конфигурация приложения для управления пользователями
class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'
