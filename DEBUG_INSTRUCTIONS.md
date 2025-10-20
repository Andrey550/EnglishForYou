# Инструкция по отладке ошибки генерации блоков

## Проблема
При нажатии кнопки "Получить новый блок" появляется ошибка: "Не удалось создать блок. Попробуйте позже."

## Что было исправлено

1. **Переделана архитектура на синхронную** - убрал проблемы с event loop в Django
2. **Добавлено детальное логирование** - теперь все ошибки записываются в `debug.log`
3. **Параллельная генерация уроков** - используется ThreadPoolExecutor для ускорения

## Как проверить логи

### Вариант 1: Через файл
```bash
# Откройте файл
D:\EnglishForYou\EnglishForYou\debug.log

# Или запустите скрипт
python D:\EnglishForYou\check_logs.py
```

### Вариант 2: Через консоль сервера
Запустите сервер и смотрите вывод в консоли:
```bash
cd D:\EnglishForYou\EnglishForYou
python manage.py runserver
```

## Что искать в логах

После нажатия кнопки "Получить новый блок" ищите:

1. **Начало генерации:**
   ```
   INFO - Generating block info for user <username>...
   ```

2. **Вызов OpenAI API:**
   ```
   INFO - Calling OpenAI API with model: meta-llama/Llama-3.3-70B-Instruct
   ```

3. **Возможные ошибки:**
   - `OpenAI API error:` - проблема с API ключом или сетью
   - `JSON parse error:` - AI вернул невалидный JSON
   - `Failed to generate block info` - не удалось создать информацию о блоке
   - `Invalid AI response` - ответ AI не прошел валидацию

## Частые причины ошибок

### 1. Проблема с API ключом
**Симптом:** `OpenAI API error: 401 Unauthorized`

**Решение:** Проверьте API ключ в `settings.py`:
```python
OPENROUTER_API_KEY = 'ваш_ключ'
```

### 2. Проблема с сетью
**Симптом:** `OpenAI API error: Connection timeout`

**Решение:** Проверьте интернет-соединение

### 3. AI вернул невалидный JSON
**Симптом:** `JSON parse error`

**Решение:** Проверьте логи, возможно нужно скорректировать промпты

### 4. Нет профиля пользователя
**Симптом:** `AttributeError: 'User' object has no attribute 'profile'`

**Решение:** Код автоматически создает профиль, но проверьте миграции:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Тестирование

### Быстрый тест через консоль Django:
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from lessons.services.lesson_ai_service import LessonAIService

# Получите пользователя
user = User.objects.get(username='admin')  # замените на ваш username

# Создайте сервис и попробуйте сгенерировать блок
service = LessonAIService()
block = service.generate_block(user)

if block:
    print(f"✓ Блок создан: {block.title}")
else:
    print("✗ Ошибка создания блока - смотрите логи")
```

## Структура генерации

Новая система работает в 4 этапа:

1. **Генерация информации о блоке** (~5-10 сек)
   - Название блока
   - Грамматическая тема
   - Описание

2. **Параллельная генерация 3 уроков** (~30-60 сек)
   - Урок грамматики
   - Урок лексики  
   - Урок чтения

Все 3 урока генерируются одновременно для ускорения!

## Если ничего не помогает

1. Перезапустите сервер Django
2. Проверьте, что установлены все зависимости:
   ```bash
   pip install openai nest-asyncio
   ```
3. Отправьте мне последние 50 строк из `debug.log`
