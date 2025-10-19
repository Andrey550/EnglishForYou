from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class LessonBlock(models.Model):
    """Блок из 3 уроков (грамматика + лексика + чтение)"""
    
    LEVEL_CHOICES = [
        ('A1', 'A1 - Начальный'),
        ('A2', 'A2 - Элементарный'),
        ('B1', 'B1 - Средний'),
        ('B2', 'B2 - Выше среднего'),
        ('C1', 'C1 - Продвинутый'),
        ('C2', 'C2 - Профессиональный'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='lesson_blocks',
        verbose_name='Пользователь'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Название блока',
        help_text='Например: Present Simple'
    )
    description = models.TextField(
        verbose_name='Описание',
        help_text='Изучение настоящего времени'
    )
    level = models.CharField(
        max_length=2,
        choices=LEVEL_CHOICES,
        verbose_name='Уровень CEFR'
    )
    difficulty_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Сложность (1-5)',
        help_text='Сложность внутри уровня'
    )
    grammar_topic = models.CharField(
        max_length=100,
        verbose_name='Грамматическая тема',
        help_text='Например: present_simple'
    )
    order = models.IntegerField(
        verbose_name='Порядковый номер',
        help_text='Порядок блока в последовательности'
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name='Все уроки пройдены'
    )
    is_passed = models.BooleanField(
        default=False,
        verbose_name='Все уроки на 80%+'
    )
    completion_percent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Процент завершения'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Завершён'
    )
    
    class Meta:
        verbose_name = 'Блок уроков'
        verbose_name_plural = 'Блоки уроков'
        ordering = ['user', 'order']
        indexes = [
            models.Index(fields=['user', 'order']),
            models.Index(fields=['user', 'is_completed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Блок {self.order}: {self.title}"


class Lesson(models.Model):
    """Урок внутри блока"""
    
    TYPE_CHOICES = [
        ('grammar', 'Грамматика'),
        ('vocabulary', 'Лексика'),
        ('reading', 'Чтение'),
    ]
    
    block = models.ForeignKey(
        LessonBlock,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Блок'
    )
    lesson_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name='Тип урока'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Название урока'
    )
    content = models.JSONField(
        verbose_name='Контент урока',
        help_text='Структура контента в JSON'
    )
    order = models.IntegerField(
        verbose_name='Порядок в блоке',
        help_text='1 - грамматика, 2 - лексика, 3 - чтение'
    )
    estimated_time = models.IntegerField(
        default=15,
        verbose_name='Примерное время (мин)'
    )
    is_unlocked = models.BooleanField(
        default=False,
        verbose_name='Разблокирован'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан'
    )
    
    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['block', 'order']
        indexes = [
            models.Index(fields=['block', 'order']),
        ]
    
    def __str__(self):
        return f"{self.block.title} - {self.get_lesson_type_display()}"


class LessonProgress(models.Model):
    """Прогресс пользователя по уроку"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
        verbose_name='Пользователь'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress',
        verbose_name='Урок'
    )
    best_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Лучший результат (%)'
    )
    current_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Текущий результат (%)'
    )
    exercises_data = models.JSONField(
        default=dict,
        verbose_name='Данные упражнений',
        help_text='{"ex1": {"answer": "...", "is_correct": true}}'
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name='Завершён'
    )
    attempts = models.IntegerField(
        default=0,
        verbose_name='Попыток'
    )
    words_learned_count = models.IntegerField(
        default=0,
        verbose_name='Выучено слов',
        help_text='Только для vocabulary'
    )
    first_completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Первое завершение'
    )
    last_accessed = models.DateTimeField(
        auto_now=True,
        verbose_name='Последний доступ'
    )
    
    class Meta:
        verbose_name = 'Прогресс урока'
        verbose_name_plural = 'Прогресс уроков'
        unique_together = ['user', 'lesson']
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['user', 'lesson']),
            models.Index(fields=['user', 'is_completed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}: {self.best_score}%"
