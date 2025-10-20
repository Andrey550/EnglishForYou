"""
Административная панель для приложения тестирования уровня английского.

Этот файл настраивает Django Admin интерфейс для управления всеми данными теста.
Админка предоставляет удобный интерфейс для просмотра и редактирования:

- Темы вопросов (Topic) - категории вопросов: грамматика, лексика, чтение, использование
- Вопросы (Question) - база вопросов с вариантами ответов и статистикой использования
- Тестовые сессии (TestSession) - история прохождения тестов пользователями
- Ответы (Answer) - детальные ответы пользователей на каждый вопрос
- Оценки по темам (TopicScore) - результаты по категориям в рамках сессии

Особенности админки:
- Цветовая индикация результатов (зеленый/желтый/красный)
- Фильтрация по всем ключевым полям
- Поиск по тексту вопросов и именам пользователей
- Встроенные редакторы (Inline) для связанных объектов
- Статистика и аналитика по вопросам
- Массовые действия для управления вопросами
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import Topic, Question, TestSession, Answer, TopicScore


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Админка для тем"""
    
    list_display = [
        'name', 
        'code', 
        'category', 
        'levels_display', 
        'questions_count',
        'is_active'
    ]
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'code', 'category', 'description')
        }),
        ('Настройки', {
            'fields': ('levels', 'is_active')
        }),
    )
    
    def levels_display(self, obj):
        """Отображение уровней"""
        return obj.levels
    levels_display.short_description = 'Уровни'
    
    def questions_count(self, obj):
        """Количество вопросов по теме"""
        count = obj.questions.filter(is_active=True).count()
        return format_html(
            '<span style="color: {};">{} вопросов</span>',
            'green' if count > 0 else 'red',
            count
        )
    questions_count.short_description = 'Вопросов'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Админка для вопросов"""
    
    list_display = [
        'id',
        'question_preview',
        'question_type',
        'level',
        'topic',
        'difficulty_score',
        'usage_statistics',
        'is_ai_generated',
        'is_active'
    ]
    list_filter = [
        'level',
        'question_type',
        'topic__category',
        'topic',
        'is_active',
        'is_ai_generated'
    ]
    search_fields = ['question_text', 'explanation']
    ordering = ['level', 'topic', 'difficulty_score']
    
    readonly_fields = [
        'usage_count', 
        'correct_rate', 
        'created_at', 
        'updated_at'
    ]
    
    fieldsets = (
        ('Вопрос', {
            'fields': ('question_text', 'question_type', 'level', 'topic')
        }),
        ('Ответы', {
            'fields': ('options', 'correct_answer', 'explanation'),
            'description': 'Для single: options=["a","b","c"], correct_answer="0". '
                          'Для multiple: correct_answer=["0","2"]. '
                          'Для text: correct_answer=["went","go"]'
        }),
        ('Настройки', {
            'fields': ('difficulty_score', 'is_active', 'is_ai_generated')
        }),
        ('Статистика', {
            'fields': ('usage_count', 'correct_rate', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_questions', 'deactivate_questions', 'reset_statistics']
    
    def question_preview(self, obj):
        """Превью вопроса"""
        preview = obj.question_text[:60]
        if len(obj.question_text) > 60:
            preview += '...'
        return preview
    question_preview.short_description = 'Вопрос'
    
    def usage_statistics(self, obj):
        """Статистика использования"""
        if obj.usage_count == 0:
            return format_html('<span style="color: gray;">Не использовался</span>')
        
        rate_percent = int(obj.correct_rate * 100)
        color = 'green' if rate_percent >= 70 else 'orange' if rate_percent >= 40 else 'red'
        
        return format_html(
            '<span style="color: {};">{}% правильных<br>({} использований)</span>',
            color,
            rate_percent,
            obj.usage_count
        )
    usage_statistics.short_description = 'Статистика'
    
    def activate_questions(self, request, queryset):
        """Активировать вопросы"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'Активировано вопросов: {count}')
    activate_questions.short_description = 'Активировать выбранные вопросы'
    
    def deactivate_questions(self, request, queryset):
        """Деактивировать вопросы"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано вопросов: {count}')
    deactivate_questions.short_description = 'Деактивировать выбранные вопросы'
    
    def reset_statistics(self, request, queryset):
        """Сбросить статистику"""
        count = queryset.update(usage_count=0, correct_rate=0.0)
        self.message_user(request, f'Статистика сброшена для {count} вопросов')
    reset_statistics.short_description = 'Сбросить статистику'


class AnswerInline(admin.TabularInline):
    """Inline для ответов в сессии"""
    model = Answer
    extra = 0
    readonly_fields = ['question', 'user_answer', 'is_correct', 'answered_at', 'time_taken']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class TopicScoreInline(admin.TabularInline):
    """Inline для оценок по темам"""
    model = TopicScore
    extra = 0
    readonly_fields = ['topic', 'questions_asked', 'correct_answers', 'percentage_display']
    can_delete = False
    
    def percentage_display(self, obj):
        """Процент с цветом"""
        percent = obj.percentage
        color = 'green' if percent >= 70 else 'orange' if percent >= 40 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            percent
        )
    percentage_display.short_description = '%'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    """Админка для сессий тестов"""
    
    list_display = [
        'id',
        'user',
        'status_display',
        'determined_level',
        'score_display',
        'started_at',
        'time_display'
    ]
    list_filter = [
        'status',
        'determined_level',
        'started_at'
    ]
    search_fields = ['user__username', 'user__email']
    ordering = ['-started_at']
    
    readonly_fields = [
        'user',
        'started_at',
        'completed_at',
        'time_spent',
        'total_questions',
        'correct_answers',
        'percentage_display',
        'category_scores_display'
    ]
    
    inlines = [TopicScoreInline, AnswerInline]
    
    fieldsets = (
        ('Информация о тесте', {
            'fields': ('user', 'status', 'determined_level')
        }),
        ('Результаты', {
            'fields': (
                'total_questions',
                'correct_answers',
                'percentage_display',
            )
        }),
        ('Оценки по категориям', {
            'fields': ('category_scores_display',)
        }),
        ('Время', {
            'fields': ('started_at', 'completed_at', 'time_spent')
        }),
        ('Детали (JSON)', {
            'fields': ('test_state',),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """Статус с цветом"""
        colors = {
            'in_progress': 'blue',
            'completed': 'green',
            'timeout': 'orange',
            'abandoned': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def score_display(self, obj):
        """Отображение результата"""
        if obj.total_questions == 0:
            return '-'
        
        percent = obj.percentage
        color = 'green' if percent >= 70 else 'orange' if percent >= 40 else 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{} ({}%)</span>',
            color,
            obj.correct_answers,
            obj.total_questions,
            percent
        )
    score_display.short_description = 'Результат'
    
    def time_display(self, obj):
        """Отображение времени"""
        if obj.time_spent == 0:
            return '-'
        
        minutes = obj.time_spent // 60
        seconds = obj.time_spent % 60
        return f'{minutes}:{seconds:02d}'
    time_display.short_description = 'Время'
    
    def percentage_display(self, obj):
        """Процент с цветом"""
        percent = obj.percentage
        color = 'green' if percent >= 70 else 'orange' if percent >= 40 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 18px;">{}%</span>',
            color,
            percent
        )
    percentage_display.short_description = 'Процент правильных'
    
    def category_scores_display(self, obj):
        """Отображение оценок по категориям"""
        scores = [
            ('Грамматика', obj.grammar_score),
            ('Словарный запас', obj.vocabulary_score),
            ('Понимание текста', obj.reading_score),
            ('Использование языка', obj.usage_score),
        ]
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        for name, score in scores:
            color = 'green' if score >= 70 else 'orange' if score >= 40 else 'red'
            html += f'''
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;">{name}</td>
                    <td style="padding: 8px; text-align: right;">
                        <span style="color: {color}; font-weight: bold;">{score}%</span>
                    </td>
                </tr>
            '''
        html += '</table>'
        
        return format_html(html)
    category_scores_display.short_description = 'Оценки по категориям'
    
    def has_add_permission(self, request):
        """Запретить создание сессий через админку"""
        return False


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """Админка для ответов"""
    
    list_display = [
        'id',
        'session_link',
        'question_preview',
        'correct_display',
        'answered_at',
        'time_taken'
    ]
    list_filter = [
        'is_correct',
        'answered_at',
        'question__level',
        'question__topic'
    ]
    search_fields = [
        'session__user__username',
        'question__question_text'
    ]
    ordering = ['-answered_at']
    
    readonly_fields = [
        'session',
        'question',
        'user_answer',
        'is_correct',
        'answered_at',
        'time_taken',
        'ai_feedback'
    ]
    
    def session_link(self, obj):
        """Ссылка на сессию"""
        return format_html(
            '<a href="/admin/start_test/testsession/{}/change/">{}</a>',
            obj.session.id,
            f"{obj.session.user.username} ({obj.session.id})"
        )
    session_link.short_description = 'Сессия'
    
    def question_preview(self, obj):
        """Превью вопроса"""
        preview = obj.question.question_text[:50]
        if len(obj.question.question_text) > 50:
            preview += '...'
        return preview
    question_preview.short_description = 'Вопрос'
    
    def correct_display(self, obj):
        """Правильность с иконкой"""
        if obj.is_correct:
            return format_html(
                '<span style="color: green; font-size: 18px;">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-size: 18px;">✗</span>'
            )
    correct_display.short_description = 'Результат'
    
    def has_add_permission(self, request):
        """Запретить создание ответов через админку"""
        return False


@admin.register(TopicScore)
class TopicScoreAdmin(admin.ModelAdmin):
    """Админка для оценок по темам"""
    
    list_display = [
        'session_link',
        'topic',
        'questions_asked',
        'correct_answers',
        'percentage_display'
    ]
    list_filter = [
        'topic__category',
        'topic'
    ]
    search_fields = [
        'session__user__username',
        'topic__name'
    ]
    ordering = ['-session__started_at']
    
    readonly_fields = [
        'session',
        'topic',
        'questions_asked',
        'correct_answers'
    ]
    
    def session_link(self, obj):
        """Ссылка на сессию"""
        return format_html(
            '<a href="/admin/start_test/testsession/{}/change/">{}</a>',
            obj.session.id,
            f"{obj.session.user.username}"
        )
    session_link.short_description = 'Пользователь'
    
    def percentage_display(self, obj):
        """Процент с цветом"""
        percent = obj.percentage
        color = 'green' if percent >= 70 else 'orange' if percent >= 40 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}%</span>',
            color,
            percent
        )
    percentage_display.short_description = 'Результат'
    
    def has_add_permission(self, request):
        """Запретить создание через админку"""
        return False
