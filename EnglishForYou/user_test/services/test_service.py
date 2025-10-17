"""
Test Service - логика адаптивного теста с AI генерацией
"""
import logging
from django.db.models import Subquery
from ..models import Question, Topic, TestSession, Answer
from .ai_service import get_ai_service

logger = logging.getLogger(__name__)


class AdaptiveTestService:
    """Сервис для управления адаптивным тестом"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def get_next_question(self, test_session, current_question_number):
        """
        Возвращает следующий вопрос.
        Каждый 5-й вопрос — через AI, иначе ищем в БД.
        """
        test_state = test_session.test_state or {}
        estimated_level = test_state.get('estimated_level', 'B1')
        recent_topics = test_state.get('recent_topics', [])

        # Subquery для исключения уже отвеченных вопросов
        answered_qs = Answer.objects.filter(session=test_session).values('question_id')
        use_ai = (current_question_number % 5 == 0)

        logger.info(f"session={getattr(test_session, 'id', None)} q#{current_question_number} level={estimated_level} AI={use_ai}")

        question = None
        if use_ai:
            try:
                question = self._generate_and_save_question(
                    level=estimated_level,
                    avoid_topics=recent_topics[-5:]
                )
                logger.info(f"AI сгенерировал вопрос: #{question.id}")
            except Exception:
                logger.error("Ошибка генерации AI вопроса", exc_info=True)
                # Фоллбек в БД
                question = (
                    self._find_question_in_db(
                        level=estimated_level,
                        answered_ids=Subquery(answered_qs),
                        avoid_topics=recent_topics[-3:]
                    )
                    or self._find_fallback_question(
                        current_level=estimated_level,
                        answered_ids=Subquery(answered_qs)
                    )
                )
        else:
            # Только БД
            logger.info(f"Поиск вопроса в БД, отвечено: {Answer.objects.filter(session=test_session).count()}")
            question = (
                self._find_question_in_db(
                    level=estimated_level,
                    answered_ids=Subquery(answered_qs),
                    avoid_topics=recent_topics[-3:]
                )
                or self._find_fallback_question(
                    current_level=estimated_level,
                    answered_ids=Subquery(answered_qs)
                )
            )

        if not question:
            logger.error("Не удалось получить вопрос")
            return None

        # Обновим recent_topics
        try:
            if getattr(question, "topic_id", None):
                recent_topics.append(question.topic.code)
                test_state["recent_topics"] = recent_topics[-10:]
                test_session.test_state = test_state
                test_session.save(update_fields=["test_state"])
        except Exception:
            logger.warning("Не удалось обновить recent_topics", exc_info=True)

        logger.info(f"Выбран вопрос: #{question.id}")
        return question
    
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
        topic = Topic.objects.filter(code=topic_code).first()
        if topic:
            return topic
        
        # Простая эвристика категории
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