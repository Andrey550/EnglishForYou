"""
Test Service - логика адаптивного теста с AI генерацией
"""
import logging
from django.db.models import Q
from ..models import Question, Topic, TestSession, Answer
from .ai_service import get_ai_service

logger = logging.getLogger(__name__)


class AdaptiveTestService:
    """Сервис для управления адаптивным тестом"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def get_next_question(self, test_session, use_ai=True):
        """
        Получает следующий вопрос для теста (из базы или генерирует через AI)
        
        Args:
            test_session: Объект TestSession
            use_ai: Использовать ли AI для генерации, если нет подходящих вопросов
        
        Returns:
            Question: Объект вопроса (сохранённый или новый)
        """
        
        test_state = test_session.test_state or {}
        estimated_level = test_state.get('estimated_level', 'B1')
        recent_topics = test_state.get('recent_topics', [])
        
        # ID уже отвеченных вопросов
        answered_ids = list(
            Answer.objects.filter(session=test_session).values_list('question_id', flat=True)
        )
        
        logger.info(f"Поиск вопроса для уровня {estimated_level}, отвечено: {len(answered_ids)}")
        
        # Попытка 1: Найти вопрос в базе на текущем уровне
        question = self._find_question_in_db(
            level=estimated_level,
            answered_ids=answered_ids,
            avoid_topics=recent_topics[-3:] if len(recent_topics) > 3 else []
        )
        
        if question:
            logger.info(f"Найден вопрос в базе: #{question.id}")
            return question
        
        # Попытка 2: Найти на соседних уровнях
        question = self._find_fallback_question(
            current_level=estimated_level,
            answered_ids=answered_ids
        )
        
        if question:
            logger.info(f"Найден fallback вопрос: #{question.id}")
            return question
        
        # Попытка 3: Генерация через AI
        if use_ai:
            logger.info(f"Генерация вопроса через AI для уровня {estimated_level}")
            try:
                question = self._generate_and_save_question(
                    level=estimated_level,
                    avoid_topics=recent_topics[-5:] if len(recent_topics) > 5 else []
                )
                logger.info(f"AI сгенерировал вопрос: #{question.id}")
                return question
            
            except Exception as e:
                logger.error(f"Ошибка генерации AI вопроса: {str(e)}")
                # Fallback на любой вопрос из базы
                question = Question.objects.filter(
                    is_active=True
                ).exclude(id__in=answered_ids).first()
                
                if question:
                    logger.warning(f"Используем запасной вопрос: #{question.id}")
                    return question
        
        # Нет доступных вопросов
        logger.error("Не удалось найти или сгенерировать вопрос")
        return None
    
    def _find_question_in_db(self, level, answered_ids, avoid_topics=None):
        """Ищет вопрос в базе данных"""
        
        query = Question.objects.filter(
            level=level,
            is_active=True
        ).exclude(id__in=answered_ids)
        
        # Избегаем недавних тем
        if avoid_topics:
            query = query.exclude(topic__code__in=avoid_topics)
        
        # Случайный выбор
        return query.order_by('?').first()
    
    def _find_fallback_question(self, current_level, answered_ids):
        """Ищет вопрос на соседних уровнях"""
        
        levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        
        try:
            current_idx = levels.index(current_level)
        except ValueError:
            current_idx = 2  # B1 по умолчанию
        
        # Сначала пробуем уровень выше
        if current_idx < len(levels) - 1:
            question = Question.objects.filter(
                level=levels[current_idx + 1],
                is_active=True
            ).exclude(id__in=answered_ids).order_by('?').first()
            
            if question:
                return question
        
        # Потом уровень ниже
        if current_idx > 0:
            question = Question.objects.filter(
                level=levels[current_idx - 1],
                is_active=True
            ).exclude(id__in=answered_ids).order_by('?').first()
            
            if question:
                return question
        
        # Любой вопрос
        return Question.objects.filter(
            is_active=True
        ).exclude(id__in=answered_ids).order_by('?').first()
    
    def _generate_and_save_question(self, level, avoid_topics=None):
        """Генерирует вопрос через AI и сохраняет в базу"""
        
        # Выбираем случайный тип вопроса
        import random
        question_types = ['single', 'multiple', 'text']
        question_type = random.choice(question_types)
        
        # Генерируем вопрос
        question_data = self.ai_service.generate_question(
            level=level,
            topic=None,  # AI выберет сам
            question_type=question_type,
            avoid_topics=avoid_topics
        )
        
        # Получаем или создаём тему
        topic_code = question_data.get('topic_code', 'general')
        topic = self._get_or_create_topic(topic_code, level)
        
        # Создаём и сохраняем вопрос
        question = Question.objects.create(
            question_text=question_data['question_text'],
            question_type=question_data['question_type'],
            level=question_data['level'],
            topic=topic,
            options=question_data.get('options', []),
            correct_answer=question_data['correct_answer'],
            explanation=question_data.get('explanation', ''),
            difficulty_score=question_data.get('difficulty_score', 50),
            is_active=True,
            is_ai_generated=True
        )
        
        logger.info(f"Создан AI вопрос #{question.id}: {question.question_text[:50]}")
        
        return question
    
    def _get_or_create_topic(self, topic_code, level):
        """Получает или создаёт тему"""
        
        # Пытаемся найти существующую тему
        topic = Topic.objects.filter(code=topic_code).first()
        
        if topic:
            return topic
        
        # Создаём новую тему
        # Определяем категорию по коду темы (простая эвристика)
        category = 'grammar'
        if 'vocab' in topic_code or 'word' in topic_code:
            category = 'vocabulary'
        elif 'read' in topic_code or 'text' in topic_code:
            category = 'reading'
        elif 'use' in topic_code or 'practice' in topic_code:
            category = 'usage'
        
        topic = Topic.objects.create(
            name=topic_code.replace('_', ' ').title(),
            code=topic_code,
            category=category,
            levels=f'{level}',
            description=f'AI-generated topic: {topic_code}',
            is_active=True
        )
        
        logger.info(f"Создана новая тема: {topic.name} ({topic.code})")
        
        return topic


# Синглтон
_test_service_instance = None

def get_test_service():
    """Возвращает синглтон Test Service"""
    global _test_service_instance
    if _test_service_instance is None:
        _test_service_instance = AdaptiveTestService()
    return _test_service_instance