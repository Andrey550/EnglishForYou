"""
Файл: lesson_ai_service.py
Описание: Сервис для асинхронной генерации уроков через OpenAI API

Этот файл содержит основной сервис для работы с AI:
- Анализ прогресса пользователя (уровень, пройденные темы, результаты тестов)
- Асинхронная генерация блоков уроков в 4 параллельных операции:
  * Операция 1: Генерация информации о блоке (название, тема, уровень)
  * Операции 2-4: Параллельная генерация 3 уроков (grammar, vocabulary, reading)
- Синхронная обертка для совместимости со старым кодом
- Валидация и сохранение сгенерированных данных в БД

Использует:
- OpenAI Python клиент для работы с API
- ThreadPoolExecutor для параллельного выполнения запросов
- asyncio.gather() для асинхронной координации задач
- Django транзакции для атомарного сохранения блоков
"""

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

# Логгер для отслеживания процесса генерации
logger = logging.getLogger(__name__)


class LessonAIService:
    """
    Сервис для генерации блоков уроков через OpenAI API
    
    Основной класс для работы с AI генерацией контента уроков.
    Поддерживает два режима:
    1. Асинхронный (generate_block_async) - рекомендуемый, быстрый
    2. Синхронный (generate_block) - для совместимости со старым кодом
    
    Использует модель: meta-llama/Llama-3.3-70B-Instruct
    API endpoint: intelligence.io.solutions
    """
    
    def __init__(self):
        """
        Инициализация AI сервиса
        
        Создает:
        - OpenAI клиент с настройками API
        - ThreadPoolExecutor для параллельного выполнения (4 потока)
        """
        # Инициализация OpenAI клиента с кастомным endpoint
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://api.intelligence.io.solutions/api/v1"
        )
        
        # Модель AI для генерации контента
        self.model = 'meta-llama/Llama-3.3-70B-Instruct'
        
        # Executor для параллельного выполнения (максимум 4 задачи одновременно)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def analyze_user_progress(self, user):
        """
        Анализ прогресса пользователя для адаптации уроков
        
        Функция собирает данные о:
        - Текущем уровне CEFR (A1-C2)
        - Следующей сложности блока (1-5)
        - Пройденных грамматических темах
        - Количестве успешно завершенных блоков
        - Результатах последнего теста (грамматика, лексика, чтение)
        
        Args:
            user: User объект Django
        Returns:
            dict с данными прогресса для построения промптов
        """
        # Проверка наличия профиля (создаем если отсутствует)
        try:
            profile = user.profile
        except AttributeError:
            # Создаём профиль автоматически если не существует
            from user.models import UserProfile
            profile = UserProfile.objects.create(user=user)
        
        # Получаем последний завершённый блок для определения следующей сложности
        last_block = LessonBlock.objects.filter(
            user=user
        ).order_by('-order').first()
        
        # Собираем список пройденных грамматических тем (для исключения повторов)
        covered_topics = list(LessonBlock.objects.filter(
            user=user
        ).values_list('grammar_topic', flat=True))
        
        # Определяем следующую сложность блока
        if last_block:
            if last_block.is_passed:
                # Если блок пройден успешно - повышаем сложность (макс 5)
                next_difficulty = min(last_block.difficulty_level + 1, 5)
            else:
                # Если блок не пройден - оставляем ту же сложность
                next_difficulty = last_block.difficulty_level
        else:
            # Если это первый блок - начинаем с сложности 1
            next_difficulty = 1
        
        # Подсчитываем количество успешно пройденных блоков (80%+)
        passed_blocks = LessonBlock.objects.filter(
            user=user,
            is_passed=True
        ).count()
        
        # Получаем результаты последнего завершенного теста
        last_test = TestSession.objects.filter(
            user=user,
            status='completed'
        ).order_by('-completed_at').first()
        
        # Формируем словарь с результатами теста (по 3 категориям)
        test_scores = {
            'grammar_score': last_test.grammar_score if last_test else 0,
            'vocabulary_score': last_test.vocabulary_score if last_test else 0,
            'reading_score': last_test.reading_score if last_test else 0,
        }
        
        # Возвращаем полный набор данных для AI
        return {
            'level': profile.language_level or 'A1',
            'difficulty': next_difficulty,
            'covered_topics': covered_topics,
            'passed_blocks': passed_blocks,
            **test_scores
        }
    
    def _call_openai(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """
        Вызов OpenAI API для генерации контента
        
        Отправляет промпт в AI и получает ответ.
        
        Args:
            prompt: текст промпта для AI
            max_tokens: максимальное количество токенов в ответе (по умолчанию 2000)
        Returns:
            str с ответом AI или None при ошибке
        """
        try:
            # Логируем вызов API
            logger.info(f"Calling OpenAI API with model: {self.model}, max_tokens: {max_tokens}")
            
            # Отправляем запрос к OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7  # Температура для креативности ответов
            )
            
            # Извлекаем текст ответа
            content = response.choices[0].message.content
            logger.info(f"OpenAI API response received, length: {len(content) if content else 0}")
            return content
        except Exception as e:
            # Логируем ошибку с полным traceback
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            return None
    
    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """
        Парсинг JSON из ответа AI
        
        AI иногда возвращает JSON обернутый в markdown блоки (```json ... ```).
        Эта функция очищает ответ и парсит чистый JSON.
        
        Args:
            content: строка с ответом от AI
        Returns:
            dict с распарсенным JSON или None при ошибке
        """
        # Проверка на пустой ответ
        if not content:
            logger.warning("Empty content received from AI")
            return None
            
        # Очищаем от markdown блоков если они есть
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]  # Убираем ```json
        if content.startswith('```'):
            content = content[3:]   # Убираем ```
        if content.endswith('```'):
            content = content[:-3]  # Убираем закрывающий ```
        content = content.strip()
        
        # Пытаемся распарсить JSON
        try:
            parsed = json.loads(content)
            logger.info(f"Successfully parsed JSON response")
            return parsed
        except json.JSONDecodeError as e:
            # Логируем ошибку парсинга с частью контента
            logger.error(f"JSON parse error: {str(e)}")
            logger.error(f"Content that failed to parse: {content[:500]}...")
            return None
    
    async def _generate_block_info_async(self, user_data: Dict, progress_data: Dict) -> Optional[Dict]:
        """
        Асинхронная генерация информации о блоке (Операция 1)
        
        Генерирует:
        - Название блока
        - Описание блока
        - Грамматическую тему
        - Уровень CEFR
        - Сложность (1-5)
        
        Args:
            user_data: dict с данными пользователя
            progress_data: dict с прогрессом
        Returns:
            dict с информацией о блоке или None при ошибке
        """
        # Получаем текущий event loop
        loop = asyncio.get_event_loop()
        
        # Строим промпт для AI
        prompt = build_block_info_prompt(user_data, progress_data)
        
        # Запускаем вызов API в executor (чтобы не блокировать event loop)
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            500  # Небольшое количество токенов для краткой информации
        )
        
        # Парсим и возвращаем JSON
        return self._parse_json_response(content)
    
    async def _generate_grammar_lesson_async(self, block_info: Dict, progress_data: Dict) -> Optional[Dict]:
        """
        Асинхронная генерация урока грамматики (Операция 2)
        
        Генерирует урок с:
        - Правилом грамматики
        - Примерами
        - 5 упражнениями (fill_blank, multiple_choice, correct_mistake)
        
        Args:
            block_info: dict с информацией о блоке
            progress_data: dict с прогрессом
        Returns:
            dict с уроком грамматики или None при ошибке
        """
        loop = asyncio.get_event_loop()
        prompt = build_grammar_lesson_prompt(block_info, progress_data)
        
        # Запускаем вызов API в executor
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            2500  # Больше токенов для правила и упражнений
        )
        
        return self._parse_json_response(content)
    
    async def _generate_vocabulary_lesson_async(self, block_info: Dict, user_data: Dict, progress_data: Dict) -> Optional[Dict]:
        """
        Асинхронная генерация урока лексики (Операция 3)
        
        Генерирует урок с:
        - 10-18 словами (зависит от сложности)
        - Переводом и примерами
        - 5 упражнениями (translate, fill_blank, matching)
        
        Args:
            block_info: dict с информацией о блоке
            user_data: dict с данными пользователя (для подбора слов по интересам)
            progress_data: dict с прогрессом
        Returns:
            dict с уроком лексики или None при ошибке
        """
        loop = asyncio.get_event_loop()
        prompt = build_vocabulary_lesson_prompt(block_info, user_data, progress_data)
        
        # Запускаем вызов API в executor
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            2500  # Токенов для списка слов и упражнений
        )
        
        return self._parse_json_response(content)
    
    async def _generate_reading_lesson_async(self, block_info: Dict, user_data: Dict, progress_data: Dict) -> Optional[Dict]:
        """
        Асинхронная генерация урока чтения (Операция 4)
        
        Генерирует урок с:
        - Текстом на английском (200-400 слов)
        - Использованием изучаемой грамматики
        - Глоссарием из 5-7 слов
        - 5 вопросами на понимание (multiple_choice, true_false, short_answer)
        
        Args:
            block_info: dict с информацией о блоке
            user_data: dict с данными пользователя (для темы текста)
            progress_data: dict с прогрессом
        Returns:
            dict с уроком чтения или None при ошибке
        """
        loop = asyncio.get_event_loop()
        prompt = build_reading_lesson_prompt(block_info, user_data, progress_data)
        
        # Запускаем вызов API в executor
        content = await loop.run_in_executor(
            self.executor,
            self._call_openai,
            prompt,
            3000  # Максимум токенов для длинного текста и вопросов
        )
        
        return self._parse_json_response(content)
    
    async def generate_block_async(self, user):
        """
        Асинхронная генерация нового блока уроков через AI (РЕКОМЕНДУЕМЫЙ МЕТОД)
        
        Это основной метод для генерации блоков в асинхронном режиме.
        Выполняет 4 операции:
        1. Генерация информации о блоке (название, тема, уровень) - ~5 сек
        2-4. Параллельная генерация 3 уроков (грамматика, лексика, чтение) - ~15 сек
        
        Общее время: ~20 секунд (вместо ~50 при последовательной генерации)
        
        Args:
            user: User объект Django
            
        Returns:
            LessonBlock объект или None при ошибке
        """
        try:
            # ЭТАП 1: Сбор данных пользователя
            try:
                profile = user.profile
            except AttributeError:
                # Создаём профиль автоматически если не существует
                from user.models import UserProfile
                profile = UserProfile.objects.create(user=user)
            
            # Данные профиля для персонализации контента
            user_data = {
                'about': profile.about or 'не указано',
                'interests': profile.interests or 'не указано',
                'learning_goals': profile.learning_goals or 'не указано',
            }
            
            # ЭТАП 2: Анализ прогресса для определения уровня и сложности
            progress_data = self.analyze_user_progress(user)
            
            # ЭТАП 3: Операция 1 - Генерация информации о блоке
            logger.info(f"Generating block info for user {user.username}...")
            block_info = await self._generate_block_info_async(user_data, progress_data)
            
            if not block_info:
                logger.error(f"Failed to generate block info for user {user.username}")
                return None
            
            # ЭТАП 4: Операции 2-4 - Параллельная генерация трех уроков
            logger.info(f"Generating lessons for user {user.username}...")
            
            # Создаем 3 асинхронные задачи
            lesson_tasks = [
                self._generate_grammar_lesson_async(block_info, progress_data),
                self._generate_vocabulary_lesson_async(block_info, user_data, progress_data),
                self._generate_reading_lesson_async(block_info, user_data, progress_data)
            ]
            
            # Запускаем все задачи параллельно и ждем завершения
            lessons_data = await asyncio.gather(*lesson_tasks)
            
            # Проверяем что все уроки успешно сгенерированы
            if None in lessons_data:
                logger.error(f"Failed to generate some lessons for user {user.username}")
                return None
            
            # ЭТАП 5: Собираем полный блок из частей
            block_data = {
                'title': block_info['title'],
                'description': block_info['description'],
                'level': block_info['level'],
                'difficulty_level': block_info['difficulty_level'],
                'grammar_topic': block_info['grammar_topic'],
                'lessons': lessons_data
            }
            
            # ЭТАП 6: Валидация структуры JSON от AI
            from lessons.utils.validators import validate_block_json
            is_valid, error_message = validate_block_json(block_data)
            
            if not is_valid:
                logger.error(f"Invalid AI response for user {user.username}: {error_message}")
                return None
            
            # ЭТАП 7: Сохранение блока в базу данных
            lesson_block = self._save_block_to_db(user, block_data, progress_data)
            
            logger.info(f"Successfully generated block for user {user.username}")
            return lesson_block
            
        except Exception as e:
            # Логируем любые неожиданные ошибки
            logger.error(f"Unexpected error generating block for user {user.username}: {str(e)}")
            return None
    
    def generate_block(self, user):
        """
        Синхронная генерация блока (для совместимости со старым кодом)
        
        Этот метод используется в Django views, которые не поддерживают async.
        Также выполняет параллельную генерацию через ThreadPoolExecutor.
        
        Этапы:
        1. Сбор данных и анализ прогресса
        2. Последовательная генерация информации о блоке
        3. Параллельная генерация 3 уроков через ThreadPoolExecutor
        4. Валидация и сохранение в БД
        
        Args:
            user: User объект Django
            
        Returns:
            LessonBlock объект или None при ошибке
        """
        try:
            # ЭТАП 1: Сбор данных пользователя
            try:
                profile = user.profile
            except AttributeError:
                # Создаём профиль автоматически если не существует
                from user.models import UserProfile
                profile = UserProfile.objects.create(user=user)
            
            # Данные профиля для персонализации
            user_data = {
                'about': profile.about or 'не указано',
                'interests': profile.interests or 'не указано',
                'learning_goals': profile.learning_goals or 'не указано',
            }
            
            # Анализ прогресса
            progress_data = self.analyze_user_progress(user)
            
            # ЭТАП 2: Генерация информации о блоке
            logger.info(f"Generating block info for user {user.username}...")
            prompt = build_block_info_prompt(user_data, progress_data)
            content = self._call_openai(prompt, 500)
            block_info = self._parse_json_response(content)
            
            if not block_info:
                logger.error(f"Failed to generate block info for user {user.username}")
                return None
            
            # ЭТАП 3: Параллельная генерация трех уроков через ThreadPoolExecutor
            logger.info(f"Generating lessons for user {user.username}...")
            
            from concurrent.futures import as_completed
            
            # Создаем список задач для параллельного выполнения
            futures = []
            
            # Задача 1: Урок грамматики
            prompt1 = build_grammar_lesson_prompt(block_info, progress_data)
            future1 = self.executor.submit(self._call_openai, prompt1, 2500)
            futures.append(('grammar', future1))
            
            # Задача 2: Урок лексики
            prompt2 = build_vocabulary_lesson_prompt(block_info, user_data, progress_data)
            future2 = self.executor.submit(self._call_openai, prompt2, 2500)
            futures.append(('vocabulary', future2))
            
            # Задача 3: Урок чтения
            prompt3 = build_reading_lesson_prompt(block_info, user_data, progress_data)
            future3 = self.executor.submit(self._call_openai, prompt3, 3000)
            futures.append(('reading', future3))
            
            # Ожидаем завершения всех задач и собираем результаты
            lessons_data = []
            for lesson_type, future in futures:
                try:
                    # Ждем результат с таймаутом 2 минуты
                    content = future.result(timeout=120)
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
            
            # Проверяем что все 3 урока сгенерированы
            if len(lessons_data) != 3:
                logger.error(f"Failed to generate all lessons for user {user.username}")
                return None
            
            # ЭТАП 4: Собираем полный блок
            block_data = {
                'title': block_info['title'],
                'description': block_info['description'],
                'level': block_info['level'],
                'difficulty_level': block_info['difficulty_level'],
                'grammar_topic': block_info['grammar_topic'],
                'lessons': lessons_data
            }
            
            # ЭТАП 5: Валидация структуры JSON от AI
            from lessons.utils.validators import validate_block_json
            is_valid, error_message = validate_block_json(block_data)
            
            if not is_valid:
                logger.error(f"Invalid AI response for user {user.username}: {error_message}")
                return None
            
            # ЭТАП 6: Сохранение блока в БД
            lesson_block = self._save_block_to_db(user, block_data, progress_data)
            
            logger.info(f"Successfully generated block for user {user.username}")
            return lesson_block
            
        except Exception as e:
            # Логируем ошибку с полным traceback
            logger.error(f"Unexpected error generating block for user {user.username}: {str(e)}", exc_info=True)
            return None
    
    def _save_block_to_db(self, user, block_data, progress_data):
        """
        Сохранение блока и уроков в базу данных
        
        Использует Django транзакцию для атомарного создания:
        - 1 блок (LessonBlock)
        - 3 урока (Lesson) внутри блока
        
        При ошибке вся операция откатывается.
        
        Args:
            user: User объект Django
            block_data: dict с данными блока от AI (title, description, level, lessons)
            progress_data: dict с данными прогресса (не используется, для будущего)
            
        Returns:
            LessonBlock объект созданного блока
        """
        # Используем транзакцию для атомарного создания (всё или ничего)
        with transaction.atomic():
            # ЭТАП 1: Определяем порядковый номер блока
            # Находим максимальный order у блоков пользователя
            last_order = LessonBlock.objects.filter(user=user).aggregate(
                Max('order')
            )['order__max'] or 0
            new_order = last_order + 1
            
            # ЭТАП 2: Создаем блок в базе данных
            lesson_block = LessonBlock.objects.create(
                user=user,
                title=block_data['title'],
                description=block_data['description'],
                level=block_data['level'],
                difficulty_level=block_data['difficulty_level'],
                grammar_topic=block_data['grammar_topic'],
                order=new_order
            )
            
            # ЭТАП 3: Создаем 3 урока внутри блока
            for index, lesson_data in enumerate(block_data['lessons'], start=1):
                lesson = Lesson.objects.create(
                    block=lesson_block,
                    lesson_type=lesson_data['lesson_type'],  # grammar, vocabulary, reading
                    title=lesson_data['title'],
                    content=lesson_data['content'],  # JSON с упражнениями
                    order=index,  # 1, 2, 3
                    is_unlocked=(index == 1)  # Только первый урок разблокирован
                )
            
            # Возвращаем созданный блок
            return lesson_block
