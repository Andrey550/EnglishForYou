"""
Модуль views для приложения тестирования уровня английского языка.

Этот модуль содержит все представления (views) для проведения адаптивного теста,
определения уровня владения английским языком и отображения результатов.

Основные компоненты:
- Вспомогательные функции для работы с временем и проверки ответов
- View-функции для управления тестовой сессией
- Функции анализа результатов и генерации рекомендаций

Author: EnglishForYou Team
Version: 1.0
"""

# ==================== ИМПОРТЫ ====================
# Django компоненты для работы с views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

# Наш сервис для адаптивной генерации вопросов
from .services.test_service import get_test_service

# Система логирования для отладки
import logging

# Модели данных нашего приложения
from .models import TestSession, Question, Answer, TopicScore

# Работа с JSON для обработки сложных структур данных
import json

# Создаем логгер для этого модуля
logger = logging.getLogger(__name__)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
# Эти функции используются другими view-функциями для выполнения
# различных вспомогательных операций: работа с временем, проверка ответов и т.д.

def get_time_remaining(session):
    """
    Вычисляет оставшееся время до окончания теста.
    
    На прохождение теста дается 30 минут (1800 секунд).
    Функция вычисляет, сколько времени осталось у пользователя.
    
    Args:
        session (TestSession): Объект текущей тестовой сессии
    
    Returns:
        int: Количество оставшихся секунд (от 0 до 1800)
        
    Примеры:
        >>> session = TestSession.objects.get(id=1)
        >>> time_left = get_time_remaining(session)
        >>> print(f"Осталось {time_left} секунд")
    """
    if session.status != 'in_progress':
        return 0

    started_at = getattr(session, 'started_at', None)
    if not started_at:
        elapsed = 0
    else:
        elapsed = (timezone.now() - started_at).total_seconds()

    remaining = 1800 - elapsed  # 30 мин = 1800 сек
    return max(0, int(remaining))


def get_time_warning(time_remaining):
    """
    Определяет уровень критичности оставшегося времени.
    
    Используется для отображения предупреждений пользователю:
    - 'critical': менее 1 минуты (красное предупреждение)
    - 'low': менее 5 минут (желтое предупреждение)
    - None: времени достаточно (без предупреждения)
    
    Args:
        time_remaining (int): Количество оставшихся секунд
    
    Returns:
        str or None: Тип предупреждения ('critical', 'low') или None
    """
    if time_remaining <= 60:
        return 'critical'  # Менее 1 минуты
    elif time_remaining <= 300:
        return 'low'  # Менее 5 минут
    return None


def format_time(seconds):
    """
    Преобразует секунды в читаемый формат MM:SS.
    
    Args:
        seconds (int): Количество секунд
    
    Returns:
        str: Время в формате "MM:SS" (например, "25:30")
        
    Примеры:
        >>> format_time(90)  # 1 минута 30 секунд
        '1:30'
        >>> format_time(3661)  # 61 минута 1 секунда
        '61:01'
    """
    seconds = int(seconds or 0)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def check_session_timeout(session):
    """
    Проверяет, не истекло ли время сессии теста.
    
    Если время истекло (прошло более 30 минут), автоматически
    завершает сессию со статусом 'timeout'.
    
    Args:
        session (TestSession): Объект тестовой сессии
    
    Returns:
        bool: True если время истекло и сессия завершена, False иначе
        
    Побочные эффекты:
        - Изменяет статус сессии на 'timeout' если время истекло
        - Сохраняет изменения в базу данных
    """
    if session.status != 'in_progress':
        return False

    if get_time_remaining(session) <= 0:
        if hasattr(session, 'timeout'):
            session.timeout()
        else:
            session.status = 'timeout'
            session.save()
        return True

    return False


def get_user_answer(request, question):
    """
    Извлекает ответ пользователя из POST-запроса.
    
    Обрабатывает разные типы вопросов:
    - 'single': один правильный ответ (радиокнопка)
    - 'multiple': несколько правильных ответов (чекбоксы)
    - 'text': текстовый ввод
    
    Args:
        request: HTTP-запрос с данными формы
        question (Question): Объект вопроса
    
    Returns:
        - str: для single и text вопросов
        - list: для multiple вопросов
        - None: если ответ не был дан
        
    Примеры:
        >>> # Для single choice вопроса
        >>> answer = get_user_answer(request, single_question)
        >>> # Вернет: '0' (индекс выбранного варианта)
        
        >>> # Для multiple choice вопроса
        >>> answers = get_user_answer(request, multi_question)
        >>> # Вернет: ['0', '2'] (индексы выбранных вариантов)
    """
    qtype = question.question_type

    if qtype == 'single':
        answer = request.POST.get('answer')
        return answer if answer not in (None, '') else None

    elif qtype == 'multiple':
        answers = request.POST.getlist('answer')
        return answers if answers else None

    elif qtype == 'text':
        answer = request.POST.get('answer', '').strip()
        return answer if answer else None

    return None


def check_answer(question, user_answer):
    """
    Проверяет правильность ответа пользователя.
    
    Универсальная функция, работающая со всеми типами вопросов.
    Автоматически нормализует и сравнивает ответы.
    
    Args:
        question (Question): Объект вопроса с правильным ответом
        user_answer: Ответ пользователя (str, list или None)
    
    Returns:
        bool: True если ответ правильный, False иначе
        
    Логика проверки:
        - single: точное совпадение индексов
        - multiple: совпадение всех выбранных вариантов
        - text: регистронезависимое сравнение с возможными вариантами
        
    Примеры:
        >>> # Проверка single choice
        >>> check_answer(question, '0')  # Выбран первый вариант
        True
        
        >>> # Проверка text ответа
        >>> check_answer(text_question, 'went')  # correct_answer: ['went', 'go']
        True
    """
    correct = getattr(question, 'correct_answer', None)
    qtype = question.question_type

    if qtype == 'single':
        if user_answer is None or correct is None:
            return False
        return str(user_answer).strip() == str(correct).strip()

    elif qtype == 'multiple':
        if user_answer is None or correct is None:
            return False
        if not isinstance(correct, list):
            correct = [correct]
        if not isinstance(user_answer, list):
            user_answer = [user_answer]
        correct_set = {str(x).strip() for x in correct}
        user_set = {str(x).strip() for x in user_answer}
        return user_set == correct_set

    elif qtype == 'text':
        if user_answer is None or correct is None:
            return False
        if not isinstance(correct, list):
            correct_list = [correct]
        else:
            correct_list = correct
        ua = str(user_answer).strip().lower()
        return ua in [str(c).strip().lower() for c in correct_list]

    return False


def update_topic_score(session, topic, is_correct):
    """
    Обновляет статистику правильных ответов по конкретной теме.
    
    Для каждой темы ведется отдельная статистика, чтобы понять,
    какие области языка нужно подтянуть пользователю.
    
    Args:
        session (TestSession): Текущая сессия теста
        topic (Topic): Тема вопроса (грамматика, лексика и т.д.)
        is_correct (bool): Был ли ответ правильным
        
    Побочные эффекты:
        - Создает или обновляет объект TopicScore
        - Увеличивает счетчики вопросов и правильных ответов
        
    Примечание:
        Функция безопасна и работает даже если метод add_answer
        отсутствует в модели TopicScore (обратная совместимость).
    """
    topic_score, _ = TopicScore.objects.get_or_create(session=session, topic=topic)
    if hasattr(topic_score, 'add_answer'):
        topic_score.add_answer(is_correct)
    else:
        if hasattr(topic_score, 'questions_asked'):
            topic_score.questions_asked = (topic_score.questions_asked or 0) + 1
        if is_correct and hasattr(topic_score, 'correct_answers'):
            topic_score.correct_answers = (topic_score.correct_answers or 0) + 1
        topic_score.save()


def update_test_state(session, question, is_correct):
    """
    Обновляет внутреннее состояние адаптивного теста.
    
    Эта функция отвечает за адаптивность теста - она корректирует
    предполагаемый уровень пользователя на основе его ответов.
    
    Args:
        session (TestSession): Текущая сессия теста
        question (Question): Вопрос на который был дан ответ
        is_correct (bool): Правильность ответа
        
    Обновляемые параметры в test_state:
        - recent_topics: последние 10 тем (для избежания повторов)
        - estimated_level: текущая оценка уровня (A1-C2)
        - question_ids: список ID показанных вопросов
        
    Алгоритм адаптации:
        - Правильный ответ -> повышаем уровень на 1 ступень
        - Неправильный ответ -> понижаем уровень на 1 ступень
        - Уровни: A1 -> A2 -> B1 -> B2 -> C1 -> C2
    """
    test_state = session.test_state or {}

    # Последние темы
    recent_topics = test_state.get('recent_topics', [])
    topic_code = getattr(question.topic, 'code', None)
    if topic_code:
        if topic_code not in recent_topics:
            recent_topics.append(topic_code)
            recent_topics = recent_topics[-10:]
    test_state['recent_topics'] = recent_topics

    # Простая коррекция оценочного уровня вверх/вниз
    current_level = test_state.get('estimated_level', 'B1')
    levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    try:
        current_idx = levels.index(current_level)
    except ValueError:
        current_idx = 2  # B1 по умолчанию

    if is_correct and current_idx < len(levels) - 1:
        test_state['estimated_level'] = levels[current_idx + 1]
    elif not is_correct and current_idx > 0:
        test_state['estimated_level'] = levels[current_idx - 1]

    # Список показанных вопросов
    used_ids = test_state.get('question_ids', [])
    if question.id not in used_ids:
        used_ids.append(question.id)
    test_state['question_ids'] = used_ids

    session.test_state = test_state


def analyze_session_simple(session):
    """
    Выполняет простой анализ результатов тестовой сессии.
    
    Определяет итоговый уровень владения языком и подсчитывает
    результаты по каждой категории (грамматика, лексика и т.д.).
    
    Args:
        session (TestSession): Завершенная сессия теста
    
    Returns:
        dict: Словарь с результатами анализа
            - level: определенный уровень (A1-C2)
            - grammar_score: процент по грамматике
            - vocabulary_score: процент по лексике
            - reading_score: процент по чтению
            - usage_score: процент по использованию языка
            
    Шкала оценок:
        90%+ -> C2 (Профессиональный)
        80%+ -> C1 (Продвинутый)
        70%+ -> B2 (Выше среднего)
        60%+ -> B1 (Средний)
        50%+ -> A2 (Элементарный)
        <50% -> A1 (Начальный)
    """
    percentage = session.percentage

    if percentage >= 90:
        level = 'C2'
    elif percentage >= 80:
        level = 'C1'
    elif percentage >= 70:
        level = 'B2'
    elif percentage >= 60:
        level = 'B1'
    elif percentage >= 50:
        level = 'A2'
    else:
        level = 'A1'

    category_scores = {}
    for category in ['grammar', 'vocabulary', 'reading', 'usage']:
        topics = TopicScore.objects.filter(session=session, topic__category=category)
        if topics.exists():
            total_correct = sum(t.correct_answers for t in topics)
            total_asked = sum(t.questions_asked for t in topics)
            category_scores[f'{category}_score'] = int((total_correct / total_asked) * 100) if total_asked > 0 else 0
        else:
            category_scores[f'{category}_score'] = percentage

    return {
        'level': level,
        **category_scores
    }


def finish_test_automatically(request, session):
    """
    Автоматически завершает тест и сохраняет результаты.
    
    Вызывается когда:
    - Пользователь ответил на все 30 вопросов
    - Истекло время теста (30 минут)
    - Пользователь досрочно завершил тест
    
    Args:
        request: HTTP-запрос
        session (TestSession): Сессия теста для завершения
    
    Returns:
        HttpResponseRedirect: Перенаправление на страницу результатов
        
    Выполняемые действия:
        1. Анализирует результаты теста
        2. Определяет уровень владения языком
        3. Сохраняет результаты в профиль пользователя
        4. Очищает данные сессии
        5. Перенаправляет на страницу с результатами
    """
    results = analyze_session_simple(session)

    session.determined_level = results['level']
    session.grammar_score = results.get('grammar_score', 0)
    session.vocabulary_score = results.get('vocabulary_score', 0)
    session.reading_score = results.get('reading_score', 0)
    session.usage_score = results.get('usage_score', 0)

    if hasattr(session, 'complete'):
        session.complete()
    else:
        session.status = 'completed'
        session.save()

    # Обновляем профиль пользователя
    profile = getattr(request.user, 'profile', None)
    if profile:
        profile.language_level = results['level']
        profile.save()

    # Очищаем Django session
    if 'test_session_id' in request.session:
        del request.session['test_session_id']

    messages.success(request, f'Тест завершён! Ваш уровень: {results["level"]}')
    return redirect('user_test:results', session_id=session.id)


# ==================== ОСНОВНЫЕ VIEW-ФУНКЦИИ ====================
# Эти функции обрабатывают HTTP-запросы пользователей и возвращают
# HTML-страницы с результатами. Каждая view отвечает за свою часть теста.

@login_required(login_url='login')
def test_intro_view(request):
    """
    Отображает приветственную страницу перед началом теста.
    
    URL: /test/
    Метод: GET
    Требует авторизации: Да
    
    На этой странице пользователь:
    - Узнает о тесте и правилах
    - Может начать новый тест
    - Может продолжить незавершенный тест
    
    Логика работы:
    1. Проверяет наличие активной сессии теста
    2. Если есть активная сессия:
       - Проверяет не истекло ли время
       - Предлагает продолжить или начать заново
    3. Отображает страницу с правилами теста
    
    Returns:
        HttpResponse: Страница test_intro.html
    """
    active_session = TestSession.objects.filter(
        user=request.user,
        status='in_progress'
    ).first()

    if active_session:
        # Проверяем истечение времени через флаг модели или через вспомогательную функцию
        is_expired_attr = getattr(active_session, 'is_expired', None)
        if is_expired_attr is True or (is_expired_attr is None and get_time_remaining(active_session) <= 0):
            if hasattr(active_session, 'timeout'):
                active_session.timeout()
            else:
                active_session.status = 'timeout'
                active_session.save()
            messages.warning(request, 'Ваш предыдущий тест был завершён по таймауту.')
        else:
            messages.info(request, 'У вас есть незавершённый тест. Хотите продолжить?')
            context = {
                'has_active_session': True,
                'active_session': active_session
            }
            return render(request, 'user_test/test_intro.html', context)

    return render(request, 'user_test/test_intro.html', {'has_active_session': False})


@login_required(login_url='login')
def start_test_view(request):
    """
    Создает новую тестовую сессию и запускает тест.
    
    URL: /test/start/
    Метод: POST
    Требует авторизации: Да
    
    POST параметры:
        agree: Флажок согласия с правилами теста
    
    Логика работы:
    1. Проверяет согласие с правилами
    2. Отменяет все активные сессии (если есть)
    3. Создает новую сессию TestSession
    4. Инициализирует test_state с начальными параметрами
    5. Сохраняет ID сессии в Django session
    6. Перенаправляет на первый вопрос
    
    Начальные параметры test_state:
        - estimated_level: 'B1' (средний уровень по умолчанию)
        - level_confidence: 0.5 (уверенность в оценке)
        - recent_topics: [] (список последних тем)
    
    Returns:
        HttpResponseRedirect: Перенаправление на /test/question/
    """
    if request.method != 'POST':
        return redirect('user_test:intro')

    if not request.POST.get('agree'):
        messages.error(request, 'Необходимо согласиться с правилами теста.')
        return redirect('user_test:intro')

    # Завершаем активные сессии
    TestSession.objects.filter(user=request.user, status='in_progress').update(status='abandoned')

    # Создаём новую сессию
    session = TestSession.objects.create(
        user=request.user,
        status='in_progress',
        test_state={
            'current_question': 0,
            'estimated_level': 'B1',
            'level_confidence': 0.5,
            'recent_topics': [],
            'difficulty_trend': 'stable',
            'question_ids': [],
        }
    )

    # Сохраняем session_id в Django session
    request.session['test_session_id'] = session.id
    request.session['test_started_at'] = timezone.now().isoformat()

    return redirect('user_test:question')


@login_required(login_url='login')
def test_question_view(request):
    """
    Главная функция теста - отображает вопросы и обрабатывает ответы.
    
    URL: /test/question/
    Методы: GET, POST
    Требует авторизации: Да
    
    GET:
        Отображает текущий вопрос теста с вариантами ответов
    
    POST:
        Обрабатывает ответ пользователя на вопрос
    
    Особенности:
    - Каждый 5-й вопрос генерируется AI
    - Остальные вопросы выбираются из базы данных
    - Тест адаптируется под уровень пользователя
    - Максимальное количество вопросов: 30
    - Ограничение по времени: 30 минут
    
    Логика работы:
    1. Проверяет наличие активной сессии
    2. Проверяет не истекло ли время
    3. Если POST - обрабатывает ответ
    4. Если GET - показывает следующий вопрос
    
    Returns:
        HttpResponse: Страница test_page.html с вопросом
        HttpResponseRedirect: Перенаправление после ответа
    """
    session_id = request.session.get('test_session_id')
    if not session_id:
        messages.error(request, 'Сессия теста не найдена. Начните тест заново.')
        return redirect('user_test:intro')

    session = get_object_or_404(TestSession, id=session_id, user=request.user)

    if session.status != 'in_progress':
        return redirect('user_test:results', session_id=session.id)

    # Проверка таймаута (через поле модели и/или вспомогательную функцию)
    if getattr(session, 'is_expired', False):
        if hasattr(session, 'timeout'):
            session.timeout()
        else:
            session.status = 'timeout'
            session.save()
        return redirect('user_test:timeout')

    if check_session_timeout(session):
        return redirect('user_test:timeout')

    if request.method == 'POST':
        return process_answer(request, session)

    return show_question(request, session)


def show_question(request, session):
    """
    Отображает следующий вопрос теста.
    
    Эта функция вызывается из test_question_view при GET-запросе.
    Она отвечает за логику получения и валидации вопроса.
    
    Основные этапы:
    1. Проверка количества отвеченных вопросов (max 30)
    2. Получение вопроса через test_service (AI или БД)
    3. Валидация вопроса (варианты, правильный ответ)
    4. Подготовка данных для отображения (прогресс, время)
    
    Args:
        request: HTTP-запрос
        session (TestSession): Текущая сессия теста
    
    Returns:
        HttpResponse: Страница test_page.html с вопросом
    """
    # Проверяем, не завершён ли тест (30 вопросов)
    if session.total_questions >= 30:
        messages.info(request, 'Вы ответили на все 30 вопросов. Тест завершён!')
        return finish_test_automatically(request, session)

    # ========== НОВЫЙ КОД: Используем test_service для получения вопроса ==========
    test_service = get_test_service()

    # Номер текущего вопроса (от 1 до 30)
    current_question_number = session.total_questions + 1

    try:
        # Получаем вопрос (каждый 5-й через AI, остальные из БД)
        question = test_service.get_next_question(
            test_session=session,
            current_question_number=current_question_number
        )

    except Exception as e:
        logger.error(f"Ошибка получения вопроса: {str(e)}")
        messages.error(request, 'Произошла ошибка при загрузке вопроса. Попробуйте ещё раз.')
        return redirect('user_test:intro')
    # ========== КОНЕЦ НОВОГО КОДА ==========

    # Вопросов нет — завершаем
    if not question:
        messages.warning(request, 'Вопросы закончились. Завершаем тест.')
        return finish_test_automatically(request, session)

    # Валидация и нормализация options
    if question.question_type in ['single', 'multiple']:
        opts = getattr(question, 'options', None)
        if opts is None:
            question.options = []
        elif not isinstance(opts, list):
            try:
                if isinstance(opts, str):
                    question.options = json.loads(opts)
                else:
                    question.options = []
            except Exception:
                question.options = []

        if len(question.options) == 0:
            messages.warning(request, f'Вопрос #{question.id} некорректный, пропускаем.')
            Answer.objects.create(
                session=session,
                question=question,
                user_answer={'skipped': True},
                is_correct=False,
                time_taken=0
            )
            session.total_questions += 1
            session.save()
            return show_question(request, session)

    elif question.question_type == 'text':
        if getattr(question, 'options', None) is None:
            question.options = []

    # Проверяем наличие правильного ответа
    if getattr(question, 'correct_answer', None) is None:
        messages.error(request, f'Вопрос #{question.id} не имеет правильного ответа, пропускаем.')
        Answer.objects.create(
            session=session,
            question=question,
            user_answer={'skipped': True},
            is_correct=False,
            time_taken=0
        )
        session.total_questions += 1
        session.save()
        return show_question(request, session)

    # Прогресс
    current_question = session.total_questions + 1
    progress_percentage = int((current_question / 30) * 100)

    # Время
    time_remaining = get_time_remaining(session)
    time_warning = get_time_warning(time_remaining)
    time_remaining_formatted = format_time(time_remaining)

    # Можно ли завершить досрочно
    can_finish = session.total_questions >= 10

    context = {
        'session': session,
        'question': question,
        'current_question': current_question,
        'total_questions': 30,
        'progress_percentage': progress_percentage,
        'time_remaining': time_remaining,
        'time_remaining_formatted': time_remaining_formatted,
        'time_warning': time_warning,
        'can_finish': can_finish,
    }

    return render(request, 'user_test/test_page.html', context)


def process_answer(request, session):
    """
    Обрабатывает ответ пользователя на вопрос теста.
    
    Вызывается из test_question_view при POST-запросе.
    
    POST параметры:
        question_id: ID вопроса
        answer: Ответ пользователя
        action: 'next' или 'finish' (для досрочного завершения)
        timeout: флаг таймаута (опционально)
    
    Основные этапы:
    1. Проверка на таймаут и досрочное завершение
    2. Получение и валидация ответа
    3. Проверка правильности ответа
    4. Сохранение ответа в базу данных
    5. Обновление статистики и адаптация теста
    6. Проверка на завершение теста (30 вопросов)
    
    Args:
        request: HTTP-запрос с данными формы
        session (TestSession): Текущая сессия теста
    
    Returns:
        HttpResponseRedirect: Перенаправление на следующий вопрос или результаты
    """
    action = request.POST.get('action', 'next')

    # Проверка на таймаут (флаг из фронтенда)
    timeout_flag = request.POST.get('timeout')
    if timeout_flag in ('true', '1', 'yes', 'True'):
        if hasattr(session, 'timeout'):
            session.timeout()
        else:
            session.status = 'timeout'
            session.save()
        return redirect('user_test:timeout')

    # Досрочное завершение
    if action == 'finish':
        return finish_test_view(request)

    # Получаем вопрос
    question_id = request.POST.get('question_id')
    if not question_id:
        messages.error(request, 'Ошибка: не передан ID вопроса.')
        return redirect('user_test:question')

    question = get_object_or_404(Question, id=question_id)

    # Извлекаем и валидируем ответ
    user_answer = get_user_answer(request, question)
    if user_answer is None:
        messages.error(request, 'Пожалуйста, выберите или введите ответ.')
        return redirect('user_test:question')

    # Проверяем правильность
    is_correct = check_answer(question, user_answer)

    # Сохраняем ответ
    Answer.objects.create(
        session=session,
        question=question,
        user_answer=user_answer,
        is_correct=is_correct,
        time_taken=0  # TODO: учесть фактическое время ответа
    )

    # Обновляем статистику вопроса
    if hasattr(question, 'update_statistics'):
        question.update_statistics(is_correct)

    # Обновляем статистику сессии
    session.total_questions += 1
    if is_correct:
        session.correct_answers += 1

    # Обновляем статистику по теме и состояние теста
    update_topic_score(session, question.topic, is_correct)
    update_test_state(session, question, is_correct)

    session.save()

    # Проверяем, завершён ли тест
    if session.total_questions >= 30:
        return finish_test_automatically(request, session)

    return redirect('user_test:question')


# ==================== ФУНКЦИИ ЗАВЕРШЕНИЯ И АНАЛИЗА РЕЗУЛЬТАТОВ ====================

def estimate_level_simple(session):
    """
    Простая оценка уровня на основе процента правильных ответов.
    
    Используется для быстрой оценки уровня владения языком.
    Может быть заменена на более сложный алгоритм в будущем.
    
    Args:
        session (TestSession): Сессия теста
    
    Returns:
        str: Уровень (A1-C2)
    
    Шкала оценки:
        >= 90% -> C2
        >= 80% -> C1
        >= 70% -> B2
        >= 55% -> B1
        >= 40% -> A2
        < 40%  -> A1
    """
    if session.total_questions == 0:
        return 'B1'

    percentage = session.percentage

    if percentage >= 90:
        return 'C2'
    elif percentage >= 80:
        return 'C1'
    elif percentage >= 70:
        return 'B2'
    elif percentage >= 55:
        return 'B1'
    elif percentage >= 40:
        return 'A2'
    else:
        return 'A1'


@login_required(login_url='login')
def finish_test_view(request):
    """
    Обрабатывает досрочное завершение теста пользователем.
    
    URL: /test/finish/
    Метод: POST
    Требует авторизации: Да
    
    Условия досрочного завершения:
    - Минимум 10 отвеченных вопросов
    - Активная сессия теста
    
    Returns:
        HttpResponseRedirect: Перенаправление на страницу результатов
    """
    if request.method != 'POST':
        return redirect('user_test:intro')

    session_id = request.session.get('test_session_id')
    if not session_id:
        return redirect('user_test:intro')

    session = get_object_or_404(TestSession, id=session_id, user=request.user)

    # Минимум 10 вопросов
    if session.total_questions < 10:
        messages.error(request, 'Необходимо ответить минимум на 10 вопросов.')
        return redirect('user_test:question')

    if hasattr(session, 'complete'):
        session.complete()
    else:
        session.status = 'completed'
        session.save()

    # Очищаем session
    if 'test_session_id' in request.session:
        del request.session['test_session_id']

    return redirect('user_test:results', session_id=session.id)


@login_required(login_url='login')
def timeout_view(request):
    """
    Обрабатывает ситуацию истечения времени теста.
    
    URL: /test/timeout/
    Метод: GET
    Требует авторизации: Да
    
    Вызывается когда прошло 30 минут с начала теста.
    
    Returns:
        HttpResponseRedirect: Перенаправление на страницу результатов
    """
    session_id = request.session.get('test_session_id')
    if not session_id:
        return redirect('user_test:intro')

    session = get_object_or_404(TestSession, id=session_id, user=request.user)

    # Завершаем по таймауту
    if session.status == 'in_progress':
        if hasattr(session, 'timeout'):
            session.timeout()
        else:
            session.status = 'timeout'
            session.save()

    # Очищаем session
    if 'test_session_id' in request.session:
        del request.session['test_session_id']

    # Показываем результаты
    return redirect('user_test:results', session_id=session.id)


@login_required(login_url='login')
def test_results_view(request, session_id):
    """
    Отображает детальные результаты теста.
    
    URL: /test/results/<session_id>/
    Метод: GET
    Требует авторизации: Да
    
    На этой странице отображается:
    - Определенный уровень владения языком
    - Процент правильных ответов
    - Результаты по категориям (грамматика, лексика и т.д.)
    - Сильные и слабые стороны
    - Рекомендации по обучению
    - Время прохождения теста
    
    Args:
        request: HTTP-запрос
        session_id (int): ID завершенной сессии теста
    
    Returns:
        HttpResponse: Страница test_results.html с результатами
    """
    session = get_object_or_404(TestSession, id=session_id, user=request.user)

    # Если тест ещё не завершён, завершаем его
    if session.status == 'in_progress':
        if hasattr(session, 'complete'):
            session.complete()
        else:
            session.status = 'completed'
            session.save()

    # Подсчитываем результаты по категориям
    calculate_category_scores(session)

    # Определяем уровень
    determined_level = determine_final_level(session)
    session.determined_level = determined_level

    # Сохраняем уровень в профиль пользователя
    profile = getattr(request.user, 'profile', None)
    if profile:
        profile.language_level = determined_level
        profile.save()

    session.save()

    # Детали для отображения
    level_info = get_level_info(determined_level)
    strengths = get_strengths(session)
    improvements = get_improvements(session)
    learning_plan = get_learning_plan(determined_level)

    # Форматируем время
    time_spent_formatted = format_time(getattr(session, 'time_spent', 0))

    # Все уровни для сравнения
    all_levels = get_all_levels()

    context = {
        'session': session,
        'level': determined_level,
        'level_name': level_info['name'],
        'level_description': level_info['description'],
        'correct_answers': session.correct_answers,
        'total_questions': session.total_questions,
        'percentage': session.percentage,
        'time_spent': time_spent_formatted,

        # Оценки по категориям
        'grammar_score': session.grammar_score,
        'vocabulary_score': session.vocabulary_score,
        'reading_score': session.reading_score,
        'usage_score': session.usage_score,

        # Рекомендации
        'strengths': strengths,
        'improvements': improvements,
        'learning_plan': learning_plan,

        # Все уровни
        'all_levels': all_levels,

        # Флаг таймаута
        'timeout': session.status == 'timeout',
    }

    return render(request, 'user_test/test_results.html', context)


# ==================== ФУНКЦИИ АНАЛИЗА И ГЕНЕРАЦИИ РЕКОМЕНДАЦИЙ ====================
# Эти функции анализируют результаты теста и генерируют персонализированные
# рекомендации для улучшения уровня английского языка.

def calculate_category_scores(session):
    """
    Подсчитывает результаты по каждой категории вопросов.
    
    Анализирует ответы пользователя и группирует их по категориям:
    - grammar (грамматика)
    - vocabulary (словарный запас)
    - reading (понимание текста)
    - usage (использование языка)
    
    Args:
        session (TestSession): Завершенная сессия теста
    
    Побочные эффекты:
        Обновляет поля session.grammar_score, vocabulary_score и т.д.
    """
    answers = Answer.objects.filter(session=session).select_related('question__topic')

    categories = {
        'grammar': {'correct': 0, 'total': 0},
        'vocabulary': {'correct': 0, 'total': 0},
        'reading': {'correct': 0, 'total': 0},
        'usage': {'correct': 0, 'total': 0},
    }

    for answer in answers:
        topic = getattr(answer.question, 'topic', None)
        category = getattr(topic, 'category', None)
        if category in categories:
            categories[category]['total'] += 1
            if answer.is_correct:
                categories[category]['correct'] += 1

    # Вычисляем проценты
    session.grammar_score = calculate_percentage(categories['grammar'])
    session.vocabulary_score = calculate_percentage(categories['vocabulary'])
    session.reading_score = calculate_percentage(categories['reading'])
    session.usage_score = calculate_percentage(categories['usage'])


def calculate_percentage(stats):
    """
    Вычисляет процент правильных ответов.
    
    Args:
        stats (dict): Словарь с полями 'total' и 'correct'
    
    Returns:
        int: Процент правильных ответов (0-100)
    """
    total = (stats.get('total') or 0)
    correct = (stats.get('correct') or 0)
    if total == 0:
        return 0
    return int((correct / total) * 100)


def determine_final_level(session):
    """
    Определяет финальный уровень владения английским языком.
    
    В текущей реализации использует простую логику,
    основанную на проценте правильных ответов.
    В будущем может быть заменена на более сложный алгоритм.
    
    Args:
        session (TestSession): Завершенная сессия теста
    
    Returns:
        str: Уровень CEFR (A1-C2)
    """
    return estimate_level_simple(session)


def get_level_info(level):
    """
    Возвращает детальную информацию об уровне CEFR.
    
    Args:
        level (str): Код уровня (A1-C2)
    
    Returns:
        dict: Словарь с полями:
            - name: Полное название уровня
            - description: Описание навыков для этого уровня
    """
    levels = {
        'A1': {
            'name': 'Начальный (Beginner)',
            'description': 'Вы можете понимать и использовать простые фразы и выражения для удовлетворения конкретных потребностей.'
        },
        'A2': {
            'name': 'Элементарный (Elementary)',
            'description': 'Вы понимаете предложения и часто используемые выражения, можете общаться в простых рутинных ситуациях.'
        },
        'B1': {
            'name': 'Средний (Intermediate)',
            'description': 'Вы можете понимать основные моменты четкой речи на знакомые темы и справляться с большинством ситуаций во время путешествий.'
        },
        'B2': {
            'name': 'Выше среднего (Upper-Intermediate)',
            'description': 'Вы понимаете основное содержание сложных текстов и можете взаимодействовать с носителями языка достаточно свободно.'
        },
        'C1': {
            'name': 'Продвинутый (Advanced)',
            'description': 'Вы понимаете широкий спектр сложных текстов и можете выражаться свободно и спонтанно без явного поиска выражений.'
        },
        'C2': {
            'name': 'Профессиональный (Proficiency)',
            'description': 'Вы легко понимаете практически всё услышанное или прочитанное и можете выражаться спонтанно, очень бегло и точно.'
        },
    }
    return levels.get(level, levels['B1'])


def get_strengths(session):
    """
    Определяет сильные стороны пользователя в изучении языка.
    
    Анализирует результаты по категориям и выявляет области,
    где пользователь показал хорошие результаты (70%+).
    
    Args:
        session (TestSession): Завершенная сессия теста
    
    Returns:
        list: Список сильных сторон (строки)
    """
    strengths = []

    scores = {
        'Грамматика': session.grammar_score,
        'Словарный запас': session.vocabulary_score,
        'Понимание текста': session.reading_score,
        'Использование языка': session.usage_score,
    }

    for name, score in scores.items():
        if score >= 70:
            strengths.append(f'{name}: отличные результаты ({score}%)')

    if not strengths:
        strengths.append('Вы показали хорошую базу для дальнейшего развития')

    return strengths


def get_improvements(session):
    """
    Определяет области, требующие улучшения.
    
    Анализирует результаты и выявляет слабые места,
    где результат ниже 50%.
    
    Args:
        session (TestSession): Завершенная сессия теста
    
    Returns:
        list: Список рекомендаций для улучшения
    """
    improvements = []

    scores = {
        'грамматику': session.grammar_score,
        'словарный запас': session.vocabulary_score,
        'понимание текста': session.reading_score,
        'практическое использование языка': session.usage_score,
    }

    for name, score in scores.items():
        if score < 50:
            improvements.append(f'Рекомендуется усилить {name}')

    if not improvements:
        improvements.append('Продолжайте практиковаться для перехода на следующий уровень')

    return improvements


def get_learning_plan(level):
    """
    Генерирует персонализированный план обучения.
    
    Создает рекомендации по изучению английского языка
    на основе определенного уровня.
    
    Args:
        level (str): Уровень CEFR (A1-C2)
    
    Returns:
        str: Текстовые рекомендации по обучению
    """
    plans = {
        'A1': 'Сосредоточьтесь на базовой грамматике, расширении словарного запаса и простых диалогах. Рекомендуем 3-4 урока в неделю по 30 минут.',
        'A2': 'Работайте над грамматическими конструкциями, активно пополняйте словарный запас и практикуйте чтение простых текстов. Рекомендуем 4-5 уроков в неделю.',
        'B1': 'Углубляйте знания грамматики, читайте адаптированную литературу и практикуйте разговорную речь. Идеально 5 уроков в неделю по 45 минут.',
        'B2': 'Изучайте сложные грамматические конструкции, читайте оригинальные тексты и активно общайтесь на английском. Рекомендуем ежедневную практику.',
        'C1': 'Совершенствуйте стиль речи, работайте над идиомами и специализированной лексикой. Погружение в языковую среду будет идеальным.',
        'C2': 'Поддерживайте уровень через чтение сложной литературы, просмотр фильмов и активное общение с носителями языка.',
    }
    return plans.get(level, plans['B1'])


def get_all_levels():
    """
    Возвращает список всех уровней CEFR для отображения.
    
    Используется для визуализации шкалы уровней
    на странице результатов.
    
    Returns:
        list: Список словарей с информацией о каждом уровне
    """
    return [
        {'code': 'A1', 'name': 'Начальный (Beginner)', 'description': 'Базовое знание языка'},
        {'code': 'A2', 'name': 'Элементарный (Elementary)', 'description': 'Понимание простых фраз'},
        {'code': 'B1', 'name': 'Средний (Intermediate)', 'description': 'Уверенное общение на знакомые темы'},
        {'code': 'B2', 'name': 'Выше среднего (Upper-Intermediate)', 'description': 'Свободное общение'},
        {'code': 'C1', 'name': 'Продвинутый (Advanced)', 'description': 'Беглое владение языком'},
        {'code': 'C2', 'name': 'Профессиональный (Proficiency)', 'description': 'Уровень носителя'},
    ]