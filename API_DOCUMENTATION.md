# 📚 API Документация EnglishForYou

## Обзор

EnglishForYou предоставляет внутренний API для работы с уроками, тестами и прогрессом пользователей.

## 🔐 Аутентификация

Все эндпоинты требуют аутентификации пользователя через Django Session Authentication.

```python
# Пример проверки аутентификации в views
@login_required
def lesson_detail(request, lesson_id):
    # ... код
```

## 📝 Основные эндпоинты

### Lessons API

#### 1. Получить список блоков уроков
```
GET /lessons/
```

**Параметры:** Нет

**Ответ:**
```html
HTML страница со списком всех блоков уроков пользователя
```

---

#### 2. Получить детали урока
```
GET /lessons/lesson/<int:lesson_id>/
```

**Параметры:**
- `lesson_id` (int) - ID урока

**Ответ:**
```html
HTML страница с деталями урока
```

---

#### 3. Сохранить прогресс урока
```
POST /lessons/save-progress/
```

**Параметры (JSON):**
```json
{
    "lesson_id": 123,
    "exercise_id": "ex_1",
    "answer": "user answer",
    "is_correct": true
}
```

**Ответ:**
```json
{
    "status": "success",
    "is_correct": true,
    "correct_answer": "правильный ответ"
}
```

---

#### 4. Завершить урок
```
POST /lessons/complete-lesson/
```

**Параметры (JSON):**
```json
{
    "lesson_id": 123,
    "score": 85,
    "time_spent": 300
}
```

**Ответ:**
```json
{
    "status": "success",
    "final_score": 85,
    "unlocked_next": true
}
```

---

#### 5. Генерация нового блока
```
POST /lessons/generate-block/
```

**Параметры (Form Data):**
- `level` (str) - Уровень CEFR (A1, A2, B1, B2, C1, C2)
- `topic` (str) - Грамматическая тема

**Ответ:**
```json
{
    "status": "success",
    "block_id": 456,
    "message": "Блок создан успешно"
}
```

---

### User Test API

#### 1. Начать тест уровня
```
GET /test/
```

**Ответ:**
```html
HTML страница с тестом
```

---

#### 2. Проверить ответ теста
```
POST /test/check-answer/
```

**Параметры (JSON):**
```json
{
    "question_id": "q_1",
    "answer": "user answer"
}
```

**Ответ:**
```json
{
    "is_correct": true,
    "correct_answer": "правильный ответ",
    "explanation": "объяснение"
}
```

---

#### 3. Завершить тест
```
POST /test/complete/
```

**Параметры (JSON):**
```json
{
    "score": 75,
    "answers": {...}
}
```

**Ответ:**
```json
{
    "status": "success",
    "determined_level": "B1",
    "recommendation": "Рекомендация"
}
```

---

### User Profile API

#### 1. Просмотр профиля
```
GET /user/profile/
```

**Ответ:**
```html
HTML страница профиля с статистикой
```

---

#### 2. Обновить профиль
```
POST /user/profile/update/
```

**Параметры (Form Data):**
- `first_name` (str)
- `last_name` (str)
- `email` (str)
- `interests` (list)

**Ответ:**
```json
{
    "status": "success",
    "message": "Профиль обновлен"
}
```

---

## 🤖 AI Service API

### LessonAIService

Сервис для генерации уроков с помощью AI.

#### Инициализация
```python
from lessons.services.lesson_ai_service import LessonAIService

service = LessonAIService()
```

#### Методы

##### generate_block()
```python
block = service.generate_block(
    user=user_instance,
    level='B1',
    topic='past_simple',
    description='Изучение прошедшего времени'
)
```

**Параметры:**
- `user` (User) - объект пользователя
- `level` (str) - уровень CEFR
- `topic` (str) - тема урока
- `description` (str, опционально) - описание

**Возвращает:**
- `LessonBlock` - созданный блок с 3 уроками

---

##### generate_block_async()
```python
import asyncio

async def create_block():
    block = await service.generate_block_async(
        user=user_instance,
        level='B1',
        topic='past_simple'
    )
    return block

# Запуск
loop = asyncio.get_event_loop()
block = loop.run_until_complete(create_block())
```

---

## 📊 Модели данных

### LessonBlock
```python
{
    "id": 1,
    "user": User,
    "title": "Past Simple",
    "description": "Изучение прошедшего времени",
    "level": "B1",
    "difficulty_level": 3,
    "grammar_topic": "past_simple",
    "order": 1,
    "created_at": "2025-01-20T12:00:00Z"
}
```

### Lesson
```python
{
    "id": 1,
    "block": LessonBlock,
    "type": "grammar",  # grammar | vocabulary | reading
    "title": "Past Simple - основы",
    "content": {...},  # JSON с контентом урока
    "order": 1,
    "duration": 15
}
```

### Progress
```python
{
    "id": 1,
    "user": User,
    "lesson": Lesson,
    "status": "completed",  # not_started | in_progress | completed
    "score": 85,
    "time_spent": 300,
    "started_at": "2025-01-20T12:00:00Z",
    "completed_at": "2025-01-20T12:05:00Z"
}
```

---

## 🔧 Вспомогательные утилиты

### check_answer()
```python
from lessons.utils.validators import check_answer

is_correct = check_answer(
    user_answer="walked",
    correct_answer="walked",
    question_type="fill_blank"
)
```

### calculate_lesson_score()
```python
from lessons.utils.progress import calculate_lesson_score

score = calculate_lesson_score(exercises=[
    {"is_correct": True},
    {"is_correct": False},
    {"is_correct": True}
])
# score = 66
```

---

## 🚨 Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Неверный запрос - отсутствуют обязательные параметры |
| 401 | Не авторизован - требуется вход |
| 403 | Доступ запрещен - нет прав на ресурс |
| 404 | Не найдено - урок или блок не существует |
| 500 | Ошибка сервера - проблема на стороне сервера |

---

## 📝 Примеры использования

### Создание и прохождение урока

```python
from django.contrib.auth.models import User
from lessons.services.lesson_ai_service import LessonAIService
from lessons.models import Lesson, Progress

# 1. Создаем блок уроков
user = User.objects.get(username='testuser')
service = LessonAIService()
block = service.generate_block(
    user=user,
    level='B1',
    topic='present_perfect'
)

# 2. Получаем первый урок
lesson = block.lessons.first()

# 3. Начинаем урок
progress = Progress.objects.create(
    user=user,
    lesson=lesson,
    status='in_progress'
)

# 4. Сохраняем ответы
# (через AJAX на фронтенде)

# 5. Завершаем урок
progress.status = 'completed'
progress.score = 85
progress.save()
```

---

## 🔗 Полезные ссылки

- [Django Documentation](https://docs.djangoproject.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [OpenRouter Documentation](https://openrouter.ai/docs)

---

**Документация актуальна на: 2025-10-20**
