from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Текстовые поля
    about = models.TextField(max_length=250, blank=True, null=True, verbose_name='О себе')
    interests = models.CharField(max_length=200, blank=True, null=True, verbose_name='Интересы')
    learning_goals = models.TextField(max_length=600, blank=True, null=True, verbose_name='Цель изучения')
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


# Автоматическое создание профиля при создании пользователя
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Создаем профиль, если его нет
    Profile.objects.get_or_create(user=instance)