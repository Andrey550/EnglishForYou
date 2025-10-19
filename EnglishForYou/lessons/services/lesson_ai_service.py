import requests
import json
import logging
from django.conf import settings
from django.db.models import Max
from django.db import transaction
from user_test.models import TestSession
from lessons.models import LessonBlock, Lesson
from .prompts import build_lesson_block_prompt

logger = logging.getLogger(__name__)


class LessonAIService:
    """Сервис для генерации блоков уроков через AI"""
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.api_url = 'https://api.intelligence.io.solutions/api/v1/chat/completions'
        self.model = 'meta-llama/Llama-3.3-70B-Instruct'
    
    def analyze_user_progress(self, user):
        """
        Анализ прогресса пользователя
        
        Returns:
            dict с данными для промпта
        """
        # Проверка наличия профиля
        try:
            profile = user.profile
        except AttributeError:
            # Создаём профиль если не существует
            from user.models import UserProfile
            profile = UserProfile.objects.create(user=user)
        
        # Последний завершённый блок
        last_block = LessonBlock.objects.filter(
            user=user
        ).order_by('-order').first()
        
        # Пройденные темы
        covered_topics = list(LessonBlock.objects.filter(
            user=user
        ).values_list('grammar_topic', flat=True))
        
        # Следующая сложность
        if last_block:
            if last_block.is_passed:
                next_difficulty = min(last_block.difficulty_level + 1, 5)
            else:
                next_difficulty = last_block.difficulty_level
        else:
            next_difficulty = 1
        
        # Количество пройденных блоков
        passed_blocks = LessonBlock.objects.filter(
            user=user,
            is_passed=True
        ).count()
        
        # Результаты последнего теста
        last_test = TestSession.objects.filter(
            user=user,
            status='completed'
        ).order_by('-completed_at').first()
        
        test_scores = {
            'grammar_score': last_test.grammar_score if last_test else 0,
            'vocabulary_score': last_test.vocabulary_score if last_test else 0,
            'reading_score': last_test.reading_score if last_test else 0,
        }
        
        return {
            'level': profile.language_level or 'A1',
            'difficulty': next_difficulty,
            'covered_topics': covered_topics,
            'passed_blocks': passed_blocks,
            **test_scores
        }
    
    def generate_block(self, user):
        """
        Генерация нового блока уроков через AI
        
        Args:
            user: User объект
            
        Returns:
            LessonBlock или None при ошибке
        """
        try:
            # Собрать данные пользователя
            try:
                profile = user.profile
            except AttributeError:
                # Создаём профиль если не существует
                from user.models import UserProfile
                profile = UserProfile.objects.create(user=user)
            
            user_data = {
                'about': profile.about or 'не указано',
                'interests': profile.interests or 'не указано',
                'learning_goals': profile.learning_goals or 'не указано',
            }
            
            # Проанализировать прогресс
            progress_data = self.analyze_user_progress(user)
            
            # Построить промпт
            prompt = build_lesson_block_prompt(user_data, progress_data)
            
            # Запрос к AI
            response = requests.post(
                self.api_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 5000,
                    'temperature': 0.7
                },
                timeout=60
            )
            
            response.raise_for_status()
            
            # Извлечь JSON из ответа
            ai_response = response.json()
            content = ai_response['choices'][0]['message']['content']
            
            # Очистить от markdown если есть
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Парсинг JSON
            block_data = json.loads(content)
            
            # Валидация JSON от AI
            from lessons.utils.validators import validate_block_json
            is_valid, error_message = validate_block_json(block_data)
            
            if not is_valid:
                logger.error(f"Invalid AI response for user {user.username}: {error_message}")
                return None
            
            # Сохранить блок в БД
            lesson_block = self._save_block_to_db(user, block_data, progress_data)
            
            return lesson_block
            
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API error for user {user.username}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for user {user.username}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating block for user {user.username}: {str(e)}")
            return None
    
    def _save_block_to_db(self, user, block_data, progress_data):
        """
        Сохранение блока в БД
        
        Args:
            user: User объект
            block_data: dict с данными блока от AI
            progress_data: dict с данными прогресса
            
        Returns:
            LessonBlock
        """
        # Используем транзакцию для атомарного создания блока и уроков
        with transaction.atomic():
            # Определить order
            last_order = LessonBlock.objects.filter(user=user).aggregate(
                Max('order')
            )['order__max'] or 0
            new_order = last_order + 1
            
            # Создать блок
            lesson_block = LessonBlock.objects.create(
                user=user,
                title=block_data['title'],
                description=block_data['description'],
                level=block_data['level'],
                difficulty_level=block_data['difficulty_level'],
                grammar_topic=block_data['grammar_topic'],
                order=new_order
            )
            
            # Создать 3 урока
            for index, lesson_data in enumerate(block_data['lessons'], start=1):
                lesson = Lesson.objects.create(
                    block=lesson_block,
                    lesson_type=lesson_data['lesson_type'],
                    title=lesson_data['title'],
                    content=lesson_data['content'],
                    order=index,
                    is_unlocked=(index == 1)  # Только первый урок разблокирован
                )
            
            return lesson_block
