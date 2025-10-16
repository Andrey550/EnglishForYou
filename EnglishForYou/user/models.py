from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator


class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Интерес')

    class Meta:
        verbose_name = 'Интерес'
        verbose_name_plural = 'Интересы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Текстовые поля
    about = models.TextField(max_length=500, blank=True, null=True, verbose_name='О себе')
    interests = models.CharField(max_length=500, blank=True, null=True, verbose_name='Интересы')
    learning_goals = models.TextField(max_length=1000, blank=True, null=True, verbose_name='Цели изучения')
    language_level = models.CharField(max_length=15, blank=True, null=True, verbose_name='Уровень владения языка')
    last_activity = models.CharField(max_length=100, blank=True, null=True, verbose_name='Последняя активность')

    # Числовые поля
    days_streak = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Дней подряд')
    words_learned = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Выученных слов')
    lessons_completed = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Уроков пройдено')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'

    # Вспомогательный парсер CSV (поддерживает старый разделитель '|')
    def _normalize_csv_to_list(self, value: str):
        if not value:
            return []
        normalized = value.replace('|', ',')
        return [x.strip() for x in normalized.split(',') if x.strip()]

    # Методы для работы с интересами
    def get_interests_list(self):
        return self._normalize_csv_to_list(self.interests)

    def set_interests_list(self, interests_list):
        items = [x.strip() for x in interests_list if x and x.strip()]
        self.interests = ','.join(items)

    # Методы для работы с целями
    def get_goals_list(self):
        return self._normalize_csv_to_list(self.learning_goals)

    def set_goals_list(self, goals_list):
        items = [x.strip() for x in goals_list if x and x.strip()]
        self.learning_goals = ','.join(items)


# Автоматическое создание профиля при создании пользователя (и подстраховка, если отсутствует)
@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)