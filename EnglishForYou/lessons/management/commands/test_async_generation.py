"""
Файл: test_async_generation.py
Описание: Django команда для тестирования асинхронной генерации уроков

Эта команда используется для проверки работы AI сервиса генерации уроков:
- Тестирует синхронную обертку generate_block()
- Тестирует асинхронный метод generate_block_async()
- Измеряет время выполнения каждой операции
- Показывает параллельную генерацию 3 уроков

Использование:
    python manage.py test_async_generation --username=admin
"""

import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from lessons.services.lesson_ai_service import LessonAIService
import time


class Command(BaseCommand):
    """
    Команда тестирования асинхронной генерации блоков уроков
    
    Функционал:
    - Запуск синхронной генерации блока
    - Запуск асинхронной генерации с детальной информацией
    - Вывод времени выполнения каждого этапа
    """
    help = 'Test async lesson generation with OpenAI'
    
    def add_arguments(self, parser):
        """Добавление аргументов командной строки"""
        # Аргумент для указания имени пользователя
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to test with'
        )
    
    def handle(self, *args, **options):
        """
        Основной метод выполнения команды
        
        Выполняет тестирование генерации уроков:
        1. Проверяет существование пользователя
        2. Запускает синхронную генерацию блока
        3. Запускает асинхронную генерацию с замерами времени
        """
        # Получаем имя пользователя из параметров
        username = options['username']
        
        # Проверяем существование пользователя в базе
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"Testing with user: {username}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} not found"))
            return
        
        # Создаем сервис для генерации уроков
        service = LessonAIService()
        
        # Заголовок теста
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Starting async lesson generation test...")
        self.stdout.write("="*60 + "\n")
        
        # Тест 1: Синхронная обертка
        self.stdout.write("Testing synchronous wrapper...")
        start_time = time.time()
        
        try:
            # Генерация блока через синхронную обертку
            block = service.generate_block(user)
            
            if block:
                # Успешно создан блок - выводим информацию
                elapsed_time = time.time() - start_time
                self.stdout.write(self.style.SUCCESS(f"✓ Block created successfully in {elapsed_time:.2f} seconds!"))
                self.stdout.write(f"  - Block title: {block.title}")
                self.stdout.write(f"  - Grammar topic: {block.grammar_topic}")
                self.stdout.write(f"  - Level: {block.level}")
                self.stdout.write(f"  - Difficulty: {block.difficulty_level}")
                
                # Выводим список созданных уроков
                lessons = block.lessons.all()
                self.stdout.write(f"\n  Lessons created: {lessons.count()}")
                for lesson in lessons:
                    self.stdout.write(f"    - {lesson.lesson_type}: {lesson.title}")
            else:
                self.stdout.write(self.style.ERROR("✗ Failed to create block"))
        
        except Exception as e:
            # Обработка ошибок при синхронной генерации
            self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))
        
        # Тест 2: Асинхронный метод напрямую
        self.stdout.write("\n" + "-"*60)
        self.stdout.write("Testing async method directly...")
        start_time = time.time()
        
        try:
            # Создаем новый event loop для асинхронного теста
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def test_async():
                """
                Асинхронная функция для тестирования генерации
                
                Выполняет 4 операции:
                1. Генерация информации о блоке
                2-4. Параллельная генерация 3 уроков (grammar, vocabulary, reading)
                """
                self.stdout.write("Starting async operations...")
                
                # Собираем данные пользователя для AI
                try:
                    profile = user.profile
                except AttributeError:
                    # Создаем профиль если не существует
                    from user.models import UserProfile
                    profile = UserProfile.objects.create(user=user)
                
                # Данные профиля пользователя
                user_data = {
                    'about': profile.about or 'не указано',
                    'interests': profile.interests or 'не указано',
                    'learning_goals': profile.learning_goals or 'не указано',
                }
                
                # Анализируем прогресс пользователя
                progress_data = service.analyze_user_progress(user)
                
                # Операция 1: Генерация информации о блоке (название, тема, уровень)
                op1_start = time.time()
                self.stdout.write("  1. Generating block info...")
                block_info = await service._generate_block_info_async(user_data, progress_data)
                op1_time = time.time() - op1_start
                
                if block_info:
                    # Информация о блоке успешно сгенерирована
                    self.stdout.write(self.style.SUCCESS(f"     ✓ Block info generated in {op1_time:.2f}s"))
                    self.stdout.write(f"       Title: {block_info.get('title')}")
                else:
                    # Ошибка генерации - останавливаем тест
                    self.stdout.write(self.style.ERROR(f"     ✗ Failed to generate block info"))
                    return None
                
                # Операции 2-4: Параллельная генерация 3 уроков
                self.stdout.write("  2-4. Generating lessons in parallel...")
                
                # Создаем 3 асинхронные задачи для уроков
                tasks_start = time.time()
                lesson_tasks = [
                    service._generate_grammar_lesson_async(block_info, progress_data),
                    service._generate_vocabulary_lesson_async(block_info, user_data, progress_data),
                    service._generate_reading_lesson_async(block_info, user_data, progress_data)
                ]
                
                # Запускаем все 3 задачи параллельно
                lessons_data = await asyncio.gather(*lesson_tasks)
                tasks_time = time.time() - tasks_start
                
                if all(lessons_data):
                    # Все уроки успешно сгенерированы
                    self.stdout.write(self.style.SUCCESS(f"     ✓ All lessons generated in {tasks_time:.2f}s"))
                    for i, lesson in enumerate(lessons_data, 1):
                        if lesson:
                            self.stdout.write(f"       Lesson {i}: {lesson.get('lesson_type')} - {lesson.get('title')}")
                else:
                    # Некоторые уроки не сгенерировались
                    self.stdout.write(self.style.ERROR("     ✗ Some lessons failed to generate"))
                
                return block_info, lessons_data
            
            # Запускаем асинхронную функцию в event loop
            result = loop.run_until_complete(test_async())
            elapsed_time = time.time() - start_time
            
            if result:
                # Тест успешно завершен
                self.stdout.write(self.style.SUCCESS(f"\n✓ Async test completed in {elapsed_time:.2f} seconds total!"))
            else:
                # Тест не прошел
                self.stdout.write(self.style.ERROR("\n✗ Async test failed"))
            
            # Закрываем event loop
            loop.close()
        
        except Exception as e:
            # Обработка ошибок асинхронного теста
            self.stdout.write(self.style.ERROR(f"✗ Async test error: {str(e)}"))
        
        # Финальное сообщение
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Test completed!")
        self.stdout.write("="*60)
