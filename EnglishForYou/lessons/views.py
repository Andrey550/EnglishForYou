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

logger = logging.getLogger(__name__)


def lessons_board_view(request):
    """
    Доска с блоками уроков
    
    URL: /lessons/board/
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Получить все блоки пользователя
    blocks = LessonBlock.objects.filter(
        user=request.user
    ).prefetch_related('lessons').order_by('order')
    
    # Подготовить данные для каждого блока
    blocks_data = []
    for block in blocks:
        lessons = block.lessons.all().order_by('order')
        
        # Определить цвет блока
        if block.is_passed:
            color_class = 'bg-green-100 border-green-300'
        elif block.is_completed and not block.is_passed:
            color_class = 'bg-red-100 border-red-300'
        else:
            color_class = 'bg-gray-50 border-gray-300'
        
        # Подготовить уроки
        lessons_data = []
        for lesson in lessons:
            # Получить прогресс
            progress = LessonProgress.objects.filter(
                user=request.user,
                lesson=lesson
            ).first()
            
            # Иконка урока
            icon_map = {
                'grammar': '📖',
                'vocabulary': '📝',
                'reading': '📚'
            }
            
            # Статус класс
            if progress and progress.is_completed:
                if progress.best_score >= 80:
                    status_class = 'text-green-600 font-semibold'
                else:
                    status_class = 'text-red-600 font-semibold'
            elif lesson.is_unlocked:
                status_class = 'text-blue-600'
            else:
                status_class = 'text-gray-400'
            
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'icon': icon_map.get(lesson.lesson_type, '📄'),
                'is_unlocked': lesson.is_unlocked,
                'status_class': status_class,
                'best_score': progress.best_score if progress else 0
            })
        
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
    
    # Определить состояние кнопки генерации
    has_incomplete_block = LessonBlock.objects.filter(
        user=request.user,
        is_completed=False
    ).exists()
    
    button_state = {
        'disabled': 'disabled' if has_incomplete_block else '',
        'text': 'Завершите текущий блок' if has_incomplete_block else '✨ Получить новый блок'
    }
    
    # Статистика пользователя
    try:
        profile = request.user.profile
        stats = {
            'days_streak': profile.days_streak,
            'lessons_completed': profile.lessons_completed,
            'words_learned': profile.words_learned
        }
    except AttributeError:
        # Если профиль не существует, создаём его
        from user.models import UserProfile
        profile = UserProfile.objects.create(user=request.user)
        stats = {
            'days_streak': 0,
            'lessons_completed': 0,
            'words_learned': 0
        }
    
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
    AJAX генерация нового блока
    
    URL: /lessons/generate/
    Method: POST
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
    
    try:
        # Проверить наличие незавершённых блоков
        has_incomplete = LessonBlock.objects.filter(
            user=request.user,
            is_completed=False
        ).exists()
        
        if has_incomplete:
            return JsonResponse({
                'success': False,
                'error': 'Завершите текущий блок перед созданием нового'
            }, status=400)
        
        # Генерация через AI
        service = LessonAIService()
        block = service.generate_block(request.user)
        
        if not block:
            return JsonResponse({
                'success': False,
                'error': 'Не удалось создать блок. Попробуйте позже.'
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'block_id': block.id,
            'message': 'Блок успешно создан!'
        })
        
    except Exception as e:
        logger.error(f"Error generating block for user {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка. Попробуйте позже.'
        }, status=500)


def lesson_detail_view(request, lesson_id):
    """
    Страница урока
    
    URL: /lessons/lesson/<int:lesson_id>/
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Получить урок
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Проверить что урок принадлежит блоку этого пользователя
    if lesson.block.user != request.user:
        return redirect('lessons_board')
    
    # Проверить разблокирован ли урок
    if not lesson.is_unlocked:
        return redirect('lessons_board')
    
    # Получить или создать прогресс
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'exercises_data': {}}
    )
    
    # Определить шаблон компонента
    component_map = {
        'grammar': 'lessons/components/grammar.html',
        'vocabulary': 'lessons/components/vocabulary.html',
        'reading': 'lessons/components/reading.html'
    }
    
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
    AJAX проверка одного упражнения (НЕ сохраняет в БД)
    
    URL: /lessons/save-progress/
    Method: POST
    Body: {lesson_id, exercise_id, user_answer}
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
    
    try:
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        exercise_id = data.get('exercise_id')
        user_answer = data.get('user_answer')
        
        # Валидация входных данных
        if not lesson_id or not exercise_id or user_answer is None:
            return JsonResponse({
                'success': False,
                'error': 'Отсутствуют обязательные параметры'
            }, status=400)
        
        # Получить урок
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Найти упражнение
        exercises = lesson.content.get('exercises', [])
        exercise = None
        
        for ex in exercises:
            if ex['id'] == exercise_id:
                exercise = ex
                break
        
        if not exercise:
            return JsonResponse({'success': False, 'error': 'Упражнение не найдено'}, status=404)
        
        # Проверить ответ
        correct_answer = exercise['correct_answer']
        is_correct = check_answer(user_answer, correct_answer)
        
        # Вернуть результат (БЕЗ правильного ответа если неправильно)
        return JsonResponse({
            'is_correct': is_correct,
            'explanation': exercise.get('explanation', ''),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Ошибка сервера'}, status=500)


@require_http_methods(["POST"])
def complete_lesson_view(request):
    """
    AJAX завершение урока (финальное сохранение)
    
    URL: /lessons/complete-lesson/
    Method: POST
    Body: {lesson_id, exercises: {...}}
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
    
    try:
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        exercises_data = data.get('exercises', {})
        
        # Валидация входных данных
        if not lesson_id:
            return JsonResponse({
                'success': False,
                'error': 'Отсутствует lesson_id'
            }, status=400)
        
        if not isinstance(exercises_data, dict):
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат exercises_data'
            }, status=400)
        
        # Получить урок
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Проверить что урок принадлежит пользователю
        if lesson.block.user != request.user:
            return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)
        
        # Получить или создать прогресс
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        
        # Подсчитать результат
        score = calculate_lesson_score(exercises_data, lesson.content)
        
        # Определить первое завершение
        is_first_completion = not progress.is_completed
        
        # Используем транзакцию для обеспечения целостности данных
        with transaction.atomic():
            # Сохранить данные
            progress.current_score = score
            progress.exercises_data = exercises_data
            progress.attempts += 1
            
            # Если результат лучше предыдущего
            if score > progress.best_score:
                progress.best_score = score
            
            # Если >= 80% - урок завершён
            if score >= 80:
                if not progress.is_completed:
                    progress.is_completed = True
                    progress.first_completed_at = timezone.now()
                
                progress.save()
                
                # Обновить статистику профиля
                update_profile_stats(request.user, lesson, score, is_first_completion)
                
                # Разблокировать следующий урок
                next_lesson = unlock_next_lesson(lesson)
                
                # Проверить завершение блока
                check_block_completion(lesson.block)
                
                return JsonResponse({
                    'success': True,
                    'score': score,
                    'is_first_completion': is_first_completion,
                    'next_lesson_unlocked': next_lesson is not None,
                    'message': 'Урок успешно завершён! 🎉'
                })
            else:
                # Не прошёл - сохраняем попытку
                progress.save()
                
                return JsonResponse({
                    'success': True,
                    'score': score,
                    'is_first_completion': False,
                    'next_lesson_unlocked': False,
                    'message': f'Результат: {score}%. Нужно минимум 80% для завершения.'
                })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f"Error completing lesson: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Ошибка сервера'}, status=500)
