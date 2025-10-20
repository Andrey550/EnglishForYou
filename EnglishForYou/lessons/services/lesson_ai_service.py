import json
import logging
import asyncio
from typing import Dict, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from django.conf import settings
from django.db.models import Max
from django.db import transaction
from user_test.models import TestSession
from lessons.models import LessonBlock, Lesson
from .prompts import (
    build_lesson_block_prompt, 
    build_block_info_prompt,
    build_grammar_lesson_prompt,
    build_vocabulary_lesson_prompt,
    build_reading_lesson_prompt
)

logger = logging.getLogger(__name__)


class LessonAIService:
    """Сервис для генерации блоков уроков через AI с использованием OpenAI"""
    
    def __init__(self):
        # Инициализация OpenAI клиента с вашим API
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://api.intelligence.io.solutions/api/v1"
        )
        self.model = 'meta-llama/Llama-3.3-70B-Instruct'
        # Executor для параллельного выполнения
        self.executor = ThreadPoolExecutor(max_workers=4)
    
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
    
    def _call_openai(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """Вызов OpenAI API"""
        try:
            logger.info(f"Calling OpenAI API with model: {self.model}, max_tokens: {max_tokens}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            content = response.choices[0].message.content
            logger.info(f"OpenAI API response received, length: {len(content) if content else 0}")
            return content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            return None
    
    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """Парсинг JSON из ответа AI"""
        if not content:
            logger.warning("Empty content received from AI")
            return None
            
        # Очистить от markdown если есть
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        try:
            parsed = json.loads(content)
            logger.info(f"Successfully parsed JSON response")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            logger.error(f"Content that failed to parse: {content[:500]}...")
            return None
    
    async def _generate_block_info_async(self, user_data: Dict, progress_data: Dict) -> Optional[Dict]:
        """Асинхронная генерация информации о блоке"""
        loop = asyncio.get_event_loop()
        prompt = build_block_info_prompt(user_data, progress_data)
        
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            500
        )
        
        return self._parse_json_response(content)
    
    async def _generate_grammar_lesson_async(self, block_info: Dict, progress_data: Dict) -> Optional[Dict]:
        """Асинхронная генерация урока грамматики"""
        loop = asyncio.get_event_loop()
        prompt = build_grammar_lesson_prompt(block_info, progress_data)
        
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            2500
        )
        
        return self._parse_json_response(content)
    
    async def _generate_vocabulary_lesson_async(self, block_info: Dict, user_data: Dict, progress_data: Dict) -> Optional[Dict]:
        """Асинхронная генерация урока лексики"""
        loop = asyncio.get_event_loop()
        prompt = build_vocabulary_lesson_prompt(block_info, user_data, progress_data)
        
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            2500
        )
        
        return self._parse_json_response(content)
    
    async def _generate_reading_lesson_async(self, block_info: Dict, user_data: Dict, progress_data: Dict) -> Optional[Dict]:
        """Асинхронная генерация урока чтения"""
        loop = asyncio.get_event_loop()
        prompt = build_reading_lesson_prompt(block_info, user_data, progress_data)
        
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            3000
        )
        
        return self._parse_json_response(content)
    
    async def generate_block_async(self, user):
        """
        Асинхронная генерация нового блока уроков через AI
        
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
            
            # Операция 1: Генерация информации о блоке
            logger.info(f"Generating block info for user {user.username}...")
            block_info = await self._generate_block_info_async(user_data, progress_data)
            
            if not block_info:
                logger.error(f"Failed to generate block info for user {user.username}")
                return None
            
            # Операции 2-4: Параллельная генерация трех уроков
            logger.info(f"Generating lessons for user {user.username}...")
            
            lesson_tasks = [
                self._generate_grammar_lesson_async(block_info, progress_data),
                self._generate_vocabulary_lesson_async(block_info, user_data, progress_data),
                self._generate_reading_lesson_async(block_info, user_data, progress_data)
            ]
            
            # Ждем завершения всех задач
            lessons_data = await asyncio.gather(*lesson_tasks)
            
            # Проверяем что все уроки сгенерированы
            if None in lessons_data:
                logger.error(f"Failed to generate some lessons for user {user.username}")
                return None
            
            # Собираем полный блок
            block_data = {
                'title': block_info['title'],
                'description': block_info['description'],
                'level': block_info['level'],
                'difficulty_level': block_info['difficulty_level'],
                'grammar_topic': block_info['grammar_topic'],
                'lessons': lessons_data
            }
            
            # Валидация JSON от AI
            from lessons.utils.validators import validate_block_json
            is_valid, error_message = validate_block_json(block_data)
            
            if not is_valid:
                logger.error(f"Invalid AI response for user {user.username}: {error_message}")
                return None
            
            # Сохранить блок в БД
            lesson_block = self._save_block_to_db(user, block_data, progress_data)
            
            logger.info(f"Successfully generated block for user {user.username}")
            return lesson_block
            
        except Exception as e:
            logger.error(f"Unexpected error generating block for user {user.username}: {str(e)}")
            return None
    
    def generate_block(self, user):
        """
        Синхронная генерация блока с параллельными вызовами через ThreadPoolExecutor
        
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
                from user.models import UserProfile
                profile = UserProfile.objects.create(user=user)
            
            user_data = {
                'about': profile.about or 'не указано',
                'interests': profile.interests or 'не указано',
                'learning_goals': profile.learning_goals or 'не указано',
            }
            
            # Проанализировать прогресс
            progress_data = self.analyze_user_progress(user)
            
            # Шаг 1: Генерация информации о блоке
            logger.info(f"Generating block info for user {user.username}...")
            prompt = build_block_info_prompt(user_data, progress_data)
            content = self._call_openai(prompt, 500)
            block_info = self._parse_json_response(content)
            
            if not block_info:
                logger.error(f"Failed to generate block info for user {user.username}")
                return None
            
            # Шаг 2-4: Параллельная генерация трех уроков
            logger.info(f"Generating lessons for user {user.username}...")
            
            from concurrent.futures import as_completed
            
            # Создаем задачи для параллельного выполнения
            futures = []
            
            # Урок 1: Грамматика
            prompt1 = build_grammar_lesson_prompt(block_info, progress_data)
            future1 = self.executor.submit(self._call_openai, prompt1, 2500)
            futures.append(('grammar', future1))
            
            # Урок 2: Лексика
            prompt2 = build_vocabulary_lesson_prompt(block_info, user_data, progress_data)
            future2 = self.executor.submit(self._call_openai, prompt2, 2500)
            futures.append(('vocabulary', future2))
            
            # Урок 3: Чтение
            prompt3 = build_reading_lesson_prompt(block_info, user_data, progress_data)
            future3 = self.executor.submit(self._call_openai, prompt3, 3000)
            futures.append(('reading', future3))
            
            # Ждем завершения всех задач и парсим результаты
            lessons_data = []
            for lesson_type, future in futures:
                try:
                    content = future.result(timeout=120)  # 2 минуты таймаут
                    lesson_data = self._parse_json_response(content)
                    if lesson_data:
                        lessons_data.append(lesson_data)
                        logger.info(f"Generated {lesson_type} lesson successfully")
                    else:
                        logger.error(f"Failed to parse {lesson_type} lesson")
                        return None
                except Exception as e:
                    logger.error(f"Error generating {lesson_type} lesson: {str(e)}")
                    return None
            
            # Проверяем что все уроки сгенерированы
            if len(lessons_data) != 3:
                logger.error(f"Failed to generate all lessons for user {user.username}")
                return None
            
            # Собираем полный блок
            block_data = {
                'title': block_info['title'],
                'description': block_info['description'],
                'level': block_info['level'],
                'difficulty_level': block_info['difficulty_level'],
                'grammar_topic': block_info['grammar_topic'],
                'lessons': lessons_data
            }
            
            # Валидация JSON от AI
            from lessons.utils.validators import validate_block_json
            is_valid, error_message = validate_block_json(block_data)
            
            if not is_valid:
                logger.error(f"Invalid AI response for user {user.username}: {error_message}")
                return None
            
            # Сохранить блок в БД
            lesson_block = self._save_block_to_db(user, block_data, progress_data)
            
            logger.info(f"Successfully generated block for user {user.username}")
            return lesson_block
            
        except Exception as e:
            logger.error(f"Unexpected error generating block for user {user.username}: {str(e)}", exc_info=True)
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
