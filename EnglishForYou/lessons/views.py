"""
Файл: views.py
Описание: Django views для работы с уроками английского языка

Этот файл содержит все view-функции для приложения lessons:
- lessons_board_view() - главная доска с блоками уроков пользователя
- generate_block_view() - AJAX генерация нового блока через AI
- lesson_detail_view() - детальная страница урока с упражнениями
- save_progress_view() - AJAX проверка одного упражнения
- complete_lesson_view() - AJAX финальное завершение урока

Используемые паттерны:
- Проверка аутентификации для всех views
- AJAX endpoints для асинхронных операций
- Django транзакции для критических операций
- Валидация входных данных
- Обработка ошибок с логированием
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import json
import logging

from .models import LessonBlock, Lesson, LessonProgress
from .services.lesson_ai_service import LessonAIService
from .utils.progress import (
    update_profile_stats,
    unlock_next_lesson,
    check_block_completion,
    calculate_lesson_score
)
from .utils.validators import check_answer

# Логгер для отслеживания ошибок
logger = logging.getLogger(__name__)


def lessons_board_view(request):
    """
    Главная доска с блоками уроков пользователя
    
    Отображает:
    - Все блоки уроков пользователя с цветовой индикацией статуса
    - Уроки внутри каждого блока с прогрессом
    - Статистику пользователя (streak, уроки, слова)
    - Кнопку генерации нового блока
    
    URL: /lessons/board/
    Template: lessons/board.html
    """
    # Проверка аутентификации
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Получаем все блоки пользователя с оптимизацией (prefetch_related)
    blocks = LessonBlock.objects.filter(
        user=request.user
    ).prefetch_related('lessons').order_by('order')
    
    # ЭТАП 1: Подготовка данных для каждого блока
    blocks_data = []
    for block in blocks:
        # Получаем все уроки блока
        lessons = block.lessons.all().order_by('order')
        
        # Определяем цвет блока на основе статуса
        if block.is_passed:
            # Блок успешно пройден (все уроки >= 80%)
            color_class = 'bg-green-100 border-green-300'
        elif block.is_completed and not block.is_passed:
            # Блок завершен, но не пройден (есть уроки < 80%)
            color_class = 'bg-red-100 border-red-300'
        else:
            # Блок в процессе прохождения
            color_class = 'bg-gray-50 border-gray-300'
        
        # ЭТАП 2: Подготовка данных для каждого урока
        lessons_data = []
        for lesson in lessons:
            # Получаем прогресс урока для пользователя
            progress = LessonProgress.objects.filter(
                user=request.user,
                lesson=lesson
            ).first()
            
            # Карта иконок для типов уроков
            icon_map = {
                'grammar': '📖',     # Грамматика
                'vocabulary': '📝',  # Лексика
                'reading': '📚'      # Чтение
            }
            
            # Определяем CSS класс статуса урока
            if progress and progress.is_completed:
                if progress.best_score >= 80:
                    # Урок успешно завершен
                    status_class = 'text-green-600 font-semibold'
                else:
                    # Урок завершен, но не пройден
                    status_class = 'text-red-600 font-semibold'
            elif lesson.is_unlocked:
                # Урок доступен для прохождения
                status_class = 'text-blue-600'
            else:
                # Урок заблокирован
                status_class = 'text-gray-400'
            
            # Добавляем данные урока
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'icon': icon_map.get(lesson.lesson_type, '📄'),
                'is_unlocked': lesson.is_unlocked,
                'status_class': status_class,
                'best_score': progress.best_score if progress else 0
            })
        
        # Добавляем данные блока
        blocks_data.append({
            'id': block.id,
            'title': block.title,
            'description': block.description,
            'level': block.level,
            'difficulty_level': block.difficulty_level,
            'order': block.order,
            'color_class': color_class,
            'is_completed': block.is_completed,
            'is_passed': block.is_passed,
            'completion_percent': block.completion_percent,
            'lessons': lessons_data
        })
    
    # ЭТАП 3: Определение состояния кнопки генерации нового блока
    # Проверяем наличие незавершенных блоков
    has_incomplete_block = LessonBlock.objects.filter(
        user=request.user,
        is_completed=False
    ).exists()
    
    # Кнопка неактивна, если есть незавершенный блок
    button_state = {
        'disabled': 'disabled' if has_incomplete_block else '',
        'text': 'Завершите текущий блок' if has_incomplete_block else '✨ Получить новый блок'
    }
    
    # ЭТАП 4: Получение статистики пользователя
    try:
        profile = request.user.profile
        stats = {
            'days_streak': profile.days_streak,
            'lessons_completed': profile.lessons_completed,
            'words_learned': profile.words_learned
        }
    except AttributeError:
        # Если профиль не существует, создаём его автоматически
        from user.models import UserProfile
        profile = UserProfile.objects.create(user=request.user)
        stats = {
            'days_streak': 0,
            'lessons_completed': 0,
            'words_learned': 0
        }
    
    # ЭТАП 5: Формирование контекста для шаблона
    context = {
        'blocks': blocks_data,
        'button': button_state,
        'stats': stats,
        'has_blocks': blocks.exists()
    }
    
    return render(request, 'lessons/board.html', context)


@require_http_methods(["POST"])
def generate_block_view(request):
    """
    AJAX endpoint для генерации нового блока уроков через AI
    
    Процесс генерации:
    1. Проверка аутентификации пользователя
    2. Проверка отсутствия незавершенных блоков
    3. Генерация блока через LessonAIService (~20-30 секунд)
    4. Возврат JSON ответа с результатом
    
    URL: /lessons/generate/
    Method: POST
    Response: JSON {success, block_id?, message?, error?}
    """
    # Проверка аутентификации
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
    
    try:
        # ЭТАП 1: Проверка наличия незавершённых блоков
        # Пользователь должен завершить текущий блок перед созданием нового
        has_incomplete = LessonBlock.objects.filter(
            user=request.user,
            is_completed=False
        ).exists()
        
        if has_incomplete:
            # Возвращаем ошибку, если есть незавершенный блок
            return JsonResponse({
                'success': False,
                'error': 'Завершите текущий блок перед созданием нового'
            }, status=400)
        
        # ЭТАП 2: Генерация блока через AI сервис
        # Создаем сервис и запускаем генерацию
        service = LessonAIService()
        block = service.generate_block(request.user)
        
        # ЭТАП 3: Проверка результата генерации
        if not block:
            # AI не смог создать блок (ошибка API, парсинга или валидации)
            return JsonResponse({
                'success': False,
                'error': 'Не удалось создать блок. Попробуйте позже.'
            }, status=500)
        
        # ЭТАП 4: Успешный ответ
        return JsonResponse({
            'success': True,
            'block_id': block.id,
            'message': 'Блок успешно создан!'
        })
        
    except Exception as e:
        # Логирование неожиданных ошибок
        logger.error(f"Error generating block for user {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка. Попробуйте позже.'
        }, status=500)


def lesson_detail_view(request, lesson_id):
    """
    Детальная страница урока с упражнениями
    
    Отображает:
    - Контент урока (правила грамматики / слова / текст для чтения)
    - 5 упражнений для проверки знаний
    - Прогресс пользователя по уроку
    - Адаптивный компонент в зависимости от типа урока
    
    Проверки безопасности:
    - Урок принадлежит пользователю
    - Урок разблокирован для прохождения
    
    URL: /lessons/lesson/<int:lesson_id>/
    Template: lessons/lesson_detail.html + component template
    """
    # Проверка аутентификации
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Получаем урок или возвращаем 404
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # ЭТАП 1: Проверка прав доступа
    # Проверяем что урок принадлежит блоку этого пользователя
    if lesson.block.user != request.user:
        return redirect('lessons_board')
    
    # ЭТАП 2: Проверка разблокировки урока
    # Урок должен быть разблокирован для прохождения
    if not lesson.is_unlocked:
        return redirect('lessons_board')
    
    # ЭТАП 3: Получение или создание прогресса урока
    # При первом входе создается запись прогресса
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'exercises_data': {}}
    )
    
    # ЭТАП 4: Определение компонента для рендеринга
    # Разные типы уроков используют разные компоненты
    component_map = {
        'grammar': 'lessons/components/grammar.html',      # Грамматический урок
        'vocabulary': 'lessons/components/vocabulary.html', # Урок лексики
        'reading': 'lessons/components/reading.html'        # Урок чтения
    }
    
    # ЭТАП 5: Формирование контекста для шаблона
    context = {
        'lesson': lesson,
        'progress': progress,
        'block': lesson.block,
        'content': lesson.content,
        'component_template': component_map.get(lesson.lesson_type, 'lessons/components/grammar.html')
    }
    
    return render(request, 'lessons/lesson_detail.html', context)


@require_http_methods(["POST"])
def save_progress_view(request):
    """
    AJAX endpoint для проверки одного упражнения
    
    ВАЖНО: Эта функция только ПРОВЕРЯЕТ ответ, но НЕ сохраняет в БД!
    Сохранение происходит только при завершении урока (complete_lesson_view).
    
    Процесс:
    1. Получение данных упражнения (lesson_id, exercise_id, user_answer)
    2. Валидация параметров
    3. Поиск упражнения в контенте урока
    4. Проверка ответа через check_answer()
    5. Возврат результата с объяснением
    
    URL: /lessons/save-progress/
    Method: POST
    Body: JSON {lesson_id, exercise_id, user_answer}
    Response: JSON {is_correct, explanation}
    """
    # Проверка аутентификации
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
    
    try:
        # ЭТАП 1: Парсинг JSON данных из тела запроса
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        exercise_id = data.get('exercise_id')
        user_answer = data.get('user_answer')
        
        # ЭТАП 2: Валидация обязательных параметров
        if not lesson_id or not exercise_id or user_answer is None:
            return JsonResponse({
                'success': False,
                'error': 'Отсутствуют обязательные параметры'
            }, status=400)
        
        # ЭТАП 3: Получение урока
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # ЭТАП 4: Поиск упражнения в контенте урока
        exercises = lesson.content.get('exercises', [])
        exercise = None
        
        # Ищем упражнение по ID
        for ex in exercises:
            if ex['id'] == exercise_id:
                exercise = ex
                break
        
        # Проверка что упражнение найдено
        if not exercise:
            return JsonResponse({'success': False, 'error': 'Упражнение не найдено'}, status=404)
        
        # ЭТАП 5: Проверка правильности ответа
        correct_answer = exercise['correct_answer']
        is_correct = check_answer(user_answer, correct_answer)
        
        # ЭТАП 6: Возврат результата
        # НЕ возвращаем правильный ответ - только результат проверки и объяснение
        return JsonResponse({
            'is_correct': is_correct,
            'explanation': exercise.get('explanation', ''),
        })
        
    except json.JSONDecodeError:
        # Ошибка парсинга JSON
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        # Логирование неожиданных ошибок
        logger.error(f"Error saving progress: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Ошибка сервера'}, status=500)


@require_http_methods(["POST"])
def complete_lesson_view(request):
    """
    AJAX endpoint для финального завершения урока
    
    Это критическая операция, которая:
    - Подсчитывает итоговый результат по всем упражнениям
    - Сохраняет прогресс в БД (в транзакции)
    - Обновляет статистику профиля (при >= 80%)
    - Разблокирует следующий урок
    - Проверяет завершение всего блока
    
    Минимальный проходной балл: 80%
    
    URL: /lessons/complete-lesson/
    Method: POST
    Body: JSON {lesson_id, exercises: {ex1: {...}, ex2: {...}, ...}}
    Response: JSON {success, score, is_first_completion, next_lesson_unlocked, message}
    """
    # Проверка аутентификации
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
    
    try:
        # ЭТАП 1: Парсинг и валидация входных данных
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        exercises_data = data.get('exercises', {})
        
        # Валидация lesson_id
        if not lesson_id:
            return JsonResponse({
                'success': False,
                'error': 'Отсутствует lesson_id'
            }, status=400)
        
        # Валидация exercises_data (должен быть словарь)
        if not isinstance(exercises_data, dict):
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат exercises_data'
            }, status=400)
        
        # ЭТАП 2: Получение урока и проверка прав доступа
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Проверяем что урок принадлежит пользователю
        if lesson.block.user != request.user:
            return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)
        
        # ЭТАП 3: Получение или создание прогресса
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        
        # ЭТАП 4: Подсчет итогового результата
        score = calculate_lesson_score(exercises_data, lesson.content)
        
        # Определяем первое ли это завершение урока (для статистики)
        is_first_completion = not progress.is_completed
        
        # ЭТАП 5: Сохранение результата в БД (атомарная операция)
        # Используем транзакцию для обеспечения целостности данных
        with transaction.atomic():
            # Сохраняем данные попытки
            progress.current_score = score
            progress.exercises_data = exercises_data
            progress.attempts += 1
            
            # Обновляем лучший результат если текущий выше
            if score > progress.best_score:
                progress.best_score = score
            
            # ЭТАП 6: Проверка прохождения урока (>= 80%)
            if score >= 80:
                # Урок успешно завершен!
                if not progress.is_completed:
                    progress.is_completed = True
                    progress.first_completed_at = timezone.now()
                
                # Сохраняем прогресс
                progress.save()
                
                # ЭТАП 7: Обновление статистики профиля
                # Увеличиваем счетчики уроков и слов
                update_profile_stats(request.user, lesson, score, is_first_completion)
                
                # ЭТАП 8: Разблокировка следующего урока в блоке
                next_lesson = unlock_next_lesson(lesson)
                
                # ЭТАП 9: Проверка завершения всего блока
                # Проверяем завершены ли все 3 урока
                check_block_completion(lesson.block)
                
                # Возвращаем успешный ответ
                return JsonResponse({
                    'success': True,
                    'score': score,
                    'is_first_completion': is_first_completion,
                    'next_lesson_unlocked': next_lesson is not None,
                    'message': 'Урок успешно завершён! 🎉'
                })
            else:
                # Урок НЕ пройден (< 80%)
                # Сохраняем попытку, но не обновляем статистику
                progress.save()
                
                return JsonResponse({
                    'success': True,
                    'score': score,
                    'is_first_completion': False,
                    'next_lesson_unlocked': False,
                    'message': f'Результат: {score}%. Нужно минимум 80% для завершения.'
                })
        
    except json.JSONDecodeError:
        # Ошибка парсинга JSON
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        # Логирование неожиданных ошибок
        logger.error(f"Error completing lesson: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Ошибка сервера'}, status=500)
