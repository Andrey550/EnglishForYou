"""
Файл: progress.py
Описание: Утилиты для работы с прогрессом пользователя по урокам

Этот файл содержит функции для:
- Обновления статистики профиля пользователя (уроки, слова)
- Управления streak (днями подряд занятий)
- Разблокировки следующих уроков
- Проверки завершения блоков
- Проверки и повышения уровня CEFR
- Подсчета результатов по упражнениям
"""

from django.utils import timezone
from datetime import timedelta
from lessons.models import LessonBlock, Lesson, LessonProgress
import logging

logger = logging.getLogger(__name__)


def update_profile_stats(user, lesson, score, is_first_completion=False):
    """
    Обновление статистики профиля пользователя
    
    Args:
        user: User объект
        lesson: Lesson объект
        score: int - результат в процентах
        is_first_completion: bool - первое завершение урока
    """
    try:
        profile = user.profile
    except AttributeError:
        # Создаём профиль если не существует
        from user.models import UserProfile
        profile = UserProfile.objects.create(user=user)
    
    # Обновляем только при первом успешном завершении
    if is_first_completion and score >= 80:
        profile.lessons_completed += 1
        
        # Если это vocabulary урок - добавляем слова
        if lesson.lesson_type == 'vocabulary':
            words_count = len(lesson.content.get('words', []))
            profile.words_learned += words_count
        
        profile.save()


def update_days_streak(user):
    """
    Обновление streak (дней подряд) при завершении блока
    
    Args:
        user: User объект
    """
    try:
        profile = user.profile
    except AttributeError:
        # Создаём профиль если не существует
        from user.models import UserProfile
        profile = UserProfile.objects.create(user=user)
    
    # Получить последний пройденный блок
    last_passed_block = LessonBlock.objects.filter(
        user=user,
        is_passed=True,
        completed_at__isnull=False
    ).order_by('-completed_at').first()
    
    if not last_passed_block:
        # Первый блок
        profile.days_streak = 1
        profile.save()
        return
    
    # Проверить дату завершения
    today = timezone.now().date()
    last_completed_date = last_passed_block.completed_at.date()
    yesterday = today - timedelta(days=1)
    
    if last_completed_date == today:
        # Уже занимались сегодня - ничего не делаем
        pass
    elif last_completed_date == yesterday:
        # Вчера занимались - увеличиваем streak
        profile.days_streak += 1
        profile.save()
    else:
        # Пропустили дни - сбрасываем на 1
        profile.days_streak = 1
        profile.save()


def unlock_next_lesson(lesson):
    """
    Разблокировка следующего урока в блоке
    
    Args:
        lesson: Lesson объект (текущий урок)
        
    Returns:
        Lesson или None
    """
    try:
        next_lesson = Lesson.objects.filter(
            block=lesson.block,
            order=lesson.order + 1
        ).first()
        
        if next_lesson and not next_lesson.is_unlocked:
            next_lesson.is_unlocked = True
            next_lesson.save()
            return next_lesson
        
        return None
        
    except Exception as e:
        logger.error(f"Error unlocking next lesson: {str(e)}")
        return None


def check_block_completion(block):
    """
    Проверка завершения блока
    
    Args:
        block: LessonBlock объект
        
    Returns:
        bool - блок завершён или нет
    """
    # Получить все уроки блока
    lessons = block.lessons.all()
    
    # Проверить что у всех уроков есть прогресс
    for lesson in lessons:
        progress = LessonProgress.objects.filter(
            lesson=lesson,
            user=block.user,
            is_completed=True
        ).first()
        
        if not progress:
            return False
    
    # Все уроки завершены
    block.is_completed = True
    block.completed_at = timezone.now()
    block.completion_percent = 100
    
    # Проверить успешность (все >= 80%)
    all_passed = True
    total_score = 0
    
    for lesson in lessons:
        progress = LessonProgress.objects.get(
            lesson=lesson,
            user=block.user
        )
        total_score += progress.best_score
        
        if progress.best_score < 80:
            all_passed = False
    
    block.is_passed = all_passed
    block.save()
    
    # Если блок пройден успешно
    if all_passed:
        # Обновить streak
        update_days_streak(block.user)
        
        # Проверить повышение уровня
        check_level_up(block.user)
    
    return True


def check_level_up(user):
    """
    Проверка и повышение уровня CEFR
    
    Args:
        user: User объект
    """
    # Количество успешно пройденных блоков
    passed_blocks_count = LessonBlock.objects.filter(
        user=user,
        is_passed=True
    ).count()
    
    # Каждые 15 блоков - повышение уровня
    if passed_blocks_count > 0 and passed_blocks_count % 15 == 0:
        try:
            profile = user.profile
        except AttributeError:
            # Создаём профиль если не существует
            from user.models import UserProfile
            profile = UserProfile.objects.create(user=user)
        current_level = profile.language_level
        
        # Карта повышения
        level_progression = {
            'A1': 'A2',
            'A2': 'B1',
            'B1': 'B2',
            'B2': 'C1',
            'C1': 'C2',
            'C2': 'C2'  # Максимальный уровень
        }
        
        new_level = level_progression.get(current_level, current_level)
        
        if new_level != current_level:
            profile.language_level = new_level
            profile.save()
            
            logger.info(f"User {user.username} leveled up: {current_level} → {new_level}")


def calculate_lesson_score(exercises_data, lesson_content):
    """
    Подсчёт процента правильных ответов
    
    Args:
        exercises_data: dict с ответами пользователя
        lesson_content: dict с контентом урока
        
    Returns:
        int - процент (0-100)
    """
    exercises = lesson_content.get('exercises', [])
    
    # Защита от деления на ноль
    if not exercises or len(exercises) == 0:
        logger.warning("No exercises found in lesson content")
        return 0
    
    correct_count = 0
    
    for exercise in exercises:
        exercise_id = exercise['id']
        
        if exercise_id in exercises_data:
            if exercises_data[exercise_id].get('is_correct', False):
                correct_count += 1
    
    return int((correct_count / len(exercises)) * 100)
