"""
Модели данных для приложения тестирования уровня английского языка.

Этот файл содержит все модели базы данных для системы адаптивного тестирования.
Модели используют стандарт CEFR (A1-C2) для определения уровней сложности.

Основные модели:
- Topic: темы вопросов (грамматика, словарный запас, чтение, использование языка)
- Question: вопросы для теста с тремя типами (single, multiple, text)
- TestSession: сессия прохождения теста пользователем с адаптивной логикой
- Answer: ответы пользователя на конкретные вопросы с проверкой правильности
- TopicScore: детальная статистика по каждой теме в рамках одной сессии

Все модели содержат подробные комментарии и вспомогательные методы для работы.
Используются валидаторы Django для обеспечения целостности данных.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class Topic(models.Model):
    """Темы для тестирования (грамматика, лексика и т.д.)"""
    
    name = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name='Название темы',
        help_text='Например: Present Simple, Articles, Vocabulary'
    )
    code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name='Код темы',
        help_text='Например: present_simple, articles'
    )
    description = models.TextField(
        blank=True, 
        verbose_name='Описание'
    )
    
    # Привязка к уровням CEFR
    levels = models.CharField(
        max_length=50, 
        verbose_name='Уровни',
        help_text='Например: A1,A2,B1',
        default='A1,A2,B1,B2,C1,C2'
    )
    
    # Категория (для группировки)
    category = models.CharField(
        max_length=50,
        choices=[
            ('grammar', 'Грамматика'),
            ('vocabulary', 'Словарный запас'),
            ('reading', 'Понимание текста'),
            ('usage', 'Использование языка'),
        ],
        default='grammar',
        verbose_name='Категория'
    )
    
    # Метаданные
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Активна'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def get_levels_list(self):
        """Возвращает список уровней"""
        return [l.strip() for l in self.levels.split(',') if l.strip()]


class Question(models.Model):
    """Вопросы для теста"""
    
    QUESTION_TYPES = [
        ('single', 'Один вариант ответа'),
        ('multiple', 'Несколько вариантов'),
        ('text', 'Текстовый ответ'),
    ]
    
    LEVELS = [
        ('A1', 'A1 - Начальный'),
        ('A2', 'A2 - Элементарный'),
        ('B1', 'B1 - Средний'),
        ('B2', 'B2 - Выше среднего'),
        ('C1', 'C1 - Продвинутый'),
        ('C2', 'C2 - Профессиональный'),
    ]
    
    # Основные поля
    question_text = models.TextField(
        verbose_name='Текст вопроса',
        help_text='Например: What ___ your name?'
    )
    question_type = models.CharField(
        max_length=10, 
        choices=QUESTION_TYPES, 
        default='single',
        verbose_name='Тип вопроса'
    )
    
    # Категоризация
    level = models.CharField(
        max_length=2, 
        choices=LEVELS, 
        verbose_name='Уровень сложности'
    )
    topic = models.ForeignKey(
        Topic, 
        on_delete=models.CASCADE, 
        related_name='questions',
        verbose_name='Тема'
    )
    
    # Варианты ответов и правильные ответы (JSON)
    options = models.JSONField(
        blank=True, 
        null=True,
        verbose_name='Варианты ответов',
        help_text='Для single/multiple: ["is", "are", "am", "be"]'
    )
    correct_answer = models.JSONField(
        verbose_name='Правильный ответ',
        help_text='Для single: "0" или "a", для multiple: ["0","1"], для text: ["went","go"]'
    )
    
    # Дополнительная информация
    explanation = models.TextField(
        blank=True, 
        verbose_name='Объяснение',
        help_text='Почему это правильный ответ'
    )
    difficulty_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Сложность (0-100)',
        help_text='0 - очень легко, 100 - очень сложно'
    )
    
    # Метаданные
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Активен'
    )
    is_ai_generated = models.BooleanField(
        default=False, 
        verbose_name='Создан AI',
        help_text='Был ли вопрос сгенерирован искусственным интеллектом'
    )
    usage_count = models.IntegerField(
        default=0,
        verbose_name='Количество использований',
        help_text='Сколько раз этот вопрос был показан пользователям'
    )
    correct_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name='Процент правильных ответов',
        help_text='От 0.0 до 1.0'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['level', 'topic', 'difficulty_score']
        indexes = [
            models.Index(fields=['level', 'topic', 'is_active']),
            models.Index(fields=['is_active', 'difficulty_score']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.topic.name}: {self.question_text[:50]}"
    
    def update_statistics(self, is_correct):
        """Обновляет статистику вопроса после ответа"""
        self.usage_count += 1
        # Пересчитываем процент правильных ответов
        if self.usage_count == 1:
            self.correct_rate = 1.0 if is_correct else 0.0
        else:
            total_correct = self.correct_rate * (self.usage_count - 1)
            if is_correct:
                total_correct += 1
            self.correct_rate = total_correct / self.usage_count
        self.save()


class TestSession(models.Model):
    """Сессия прохождения теста пользователем"""
    
    STATUS_CHOICES = [
        ('in_progress', 'В процессе'),
        ('completed', 'Завершён'),
        ('timeout', 'Время истекло'),
        ('abandoned', 'Прерван'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='test_sessions',
        verbose_name='Пользователь'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='in_progress',
        verbose_name='Статус'
    )
    
    # Результаты
    determined_level = models.CharField(
        max_length=2, 
        blank=True, 
        null=True,
        choices=Question.LEVELS,
        verbose_name='Определённый уровень'
    )
    total_questions = models.IntegerField(
        default=0,
        verbose_name='Всего вопросов'
    )
    correct_answers = models.IntegerField(
        default=0,
        verbose_name='Правильных ответов'
    )
    
    # Детальная информация (JSON)
    test_state = models.JSONField(
        default=dict,
        verbose_name='Состояние теста',
        help_text='История ответов, анализ по темам и т.д.'
    )
    
    # Анализ по категориям
    grammar_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Грамматика (%)'
    )
    vocabulary_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Словарный запас (%)'
    )
    reading_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Понимание текста (%)'
    )
    usage_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Использование языка (%)'
    )
    
    # Временные метки
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Начало теста'
    )
    completed_at = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name='Завершение теста'
    )
    time_spent = models.IntegerField(
        default=0, 
        verbose_name='Время (секунды)',
        help_text='Фактическое время прохождения'
    )
    
    class Meta:
        verbose_name = 'Сессия теста'
        verbose_name_plural = 'Сессии тестов'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['-started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def percentage(self):
        """Процент правильных ответов"""
        if self.total_questions > 0:
            return round((self.correct_answers / self.total_questions) * 100)
        return 0
    
    @property
    def time_remaining(self):
        """Оставшееся время в секундах"""
        if self.status != 'in_progress':
            return 0
        
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = 1800 - elapsed  # 30 минут = 1800 секунд
        return max(0, int(remaining))
    
    @property
    def is_expired(self):
        """Истекло ли время"""
        return self.time_remaining <= 0
    
    def complete(self):
        """Завершить тест"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.time_spent = int((self.completed_at - self.started_at).total_seconds())
        self.save()
    
    def timeout(self):
        """Завершить по таймауту"""
        self.status = 'timeout'
        self.completed_at = timezone.now()
        self.time_spent = 1800  # Максимальное время
        self.save()


class Answer(models.Model):
    """Ответ пользователя на конкретный вопрос"""
    
    session = models.ForeignKey(
        TestSession, 
        on_delete=models.CASCADE, 
        related_name='answers',
        verbose_name='Сессия'
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE,
        verbose_name='Вопрос'
    )
    
    # Ответ пользователя
    user_answer = models.JSONField(
        verbose_name='Ответ пользователя',
        help_text='Для single: "0", для multiple: ["0","1"], для text: "went"'
    )
    is_correct = models.BooleanField(
        verbose_name='Правильно'
    )
    
    # AI анализ (опционально)
    ai_feedback = models.TextField(
        blank=True, 
        verbose_name='AI анализ',
        help_text='Детальный анализ ответа от AI'
    )
    
    # Временные метки
    answered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время ответа'
    )
    time_taken = models.IntegerField(
        default=0,
        verbose_name='Время на ответ (сек)',
        help_text='Сколько секунд думал пользователь'
    )
    
    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'
        ordering = ['answered_at']
        indexes = [
            models.Index(fields=['session', 'answered_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.question.question_text[:30]}"


class TopicScore(models.Model):
    """Оценка пользователя по конкретной теме в рамках сессии"""
    
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name='topic_scores',
        verbose_name='Сессия'
    )
    topic = models.ForeignKey(
        Topic, 
        on_delete=models.CASCADE,
        verbose_name='Тема'
    )
    
    # Статистика
    questions_asked = models.IntegerField(
        default=0,
        verbose_name='Задано вопросов'
    )
    correct_answers = models.IntegerField(
        default=0,
        verbose_name='Правильных ответов'
    )
    
    class Meta:
        verbose_name = 'Оценка по теме'
        verbose_name_plural = 'Оценки по темам'
        unique_together = ['session', 'topic']
        indexes = [
            models.Index(fields=['session', 'topic']),
        ]
    
    @property
    def percentage(self):
        """Процент правильных ответов по теме"""
        if self.questions_asked > 0:
            return round((self.correct_answers / self.questions_asked) * 100)
        return 0
    
    def __str__(self):
        return f"{self.session.user.username} - {self.topic.name}: {self.percentage}%"
    
    def add_answer(self, is_correct):
        """Добавить ответ в статистику темы"""
        self.questions_asked += 1
        if is_correct:
            self.correct_answers += 1
        self.save()
