# 🔧 Решение проблем EnglishForYou

Руководство по устранению распространенных проблем.

## 📋 Содержание

- [Проблемы установки](#-проблемы-установки)
- [Проблемы запуска](#-проблемы-запуска)
- [Проблемы с AI генерацией](#-проблемы-с-ai-генерацией)
- [Проблемы с базой данных](#-проблемы-с-базой-данных)
- [Проблемы с пользователями](#-проблемы-с-пользователями)
- [Проблемы производительности](#-проблемы-производительности)

---

## 🔨 Проблемы установки

### Ошибка: `python` не найден

**Проблема:**
```
'python' is not recognized as an internal or external command
```

**Решение:**
```bash
# Убедитесь, что Python установлен
python --version

# Если не работает, попробуйте:
python3 --version
py --version

# Добавьте Python в PATH:
# Windows: Системные настройки → Переменные среды → Path
```

---

### Ошибка: pip не установлен

**Проблема:**
```
'pip' is not recognized as an internal or external command
```

**Решение:**
```bash
# Установите pip
python -m ensurepip --upgrade

# Или используйте:
python -m pip install --upgrade pip
```

---

### Ошибка при установке зависимостей

**Проблема:**
```
ERROR: Could not find a version that satisfies the requirement Django==5.2.6
```

**Решение:**
```bash
# Обновите pip
python -m pip install --upgrade pip

# Установите зависимости по одной
pip install Django==5.2.6
pip install openai==1.50.0
pip install python-dotenv==1.0.1

# Проверьте версию Python (требуется 3.10+)
python --version
```

---

## 🚀 Проблемы запуска

### Ошибка: порт 8000 уже занят

**Проблема:**
```
Error: That port is already in use.
```

**Решение:**
```bash
# Вариант 1: Используйте другой порт
python manage.py runserver 8080

# Вариант 2: Найдите и завершите процесс (Windows)
netstat -ano | findstr :8000
taskkill /PID <номер_процесса> /F

# Вариант 3: Найдите и завершите процесс (Linux/Mac)
lsof -ti:8000 | xargs kill -9
```

---

### Ошибка: ModuleNotFoundError

**Проблема:**
```
ModuleNotFoundError: No module named 'django'
```

**Решение:**
```bash
# Убедитесь, что виртуальное окружение активировано
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt
```

---

### Ошибка: миграции не применены

**Проблема:**
```
You have 18 unapplied migration(s). Your project may not work properly until you apply the migrations.
```

**Решение:**
```bash
cd EnglishForYou
python manage.py migrate
```

---

## 🤖 Проблемы с AI генерацией

### Ошибка: API ключ не работает

**Проблема:**
```
Error: Authentication failed - Invalid API key
```

**Решение:**
1. Проверьте API ключ в `settings.py`:
```python
OPENROUTER_API_KEY = 'ваш_ключ_здесь'
```

2. Убедитесь, что ключ активен на openrouter.ai
3. Проверьте баланс аккаунта
4. Попробуйте сгенерировать новый ключ

---

### Ошибка: timeout при генерации

**Проблема:**
```
TimeoutError: Request timed out after 30 seconds
```

**Решение:**
```python
# В lessons/services/lesson_ai_service.py
# Увеличьте timeout:
client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://intelligence.io.solutions/v1",
    timeout=60.0  # Увеличьте с 30 до 60 секунд
)
```

---

### Ошибка: некорректный JSON от AI

**Проблема:**
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Решение:**
1. Проверьте логи в `debug.log`
2. Попробуйте другую AI модель:
```python
AI_SETTINGS = {
    'MODEL': 'gpt-3.5-turbo',  # Вместо Llama
    ...
}
```
3. Проверьте промпты в `lessons/services/prompts.py`

---

### Генерация уроков слишком медленная

**Проблема:**
Создание блока занимает больше минуты

**Решение:**
1. Используйте более быструю модель
2. Уменьшите MAX_TOKENS в настройках:
```python
AI_SETTINGS = {
    'MAX_TOKENS': 3000,  # Вместо 5000
    ...
}
```
3. Проверьте скорость интернета

---

## 💾 Проблемы с базой данных

### Ошибка: база данных заблокирована

**Проблема:**
```
OperationalError: database is locked
```

**Решение:**
```bash
# Закройте все процессы Django
# Удалите файл блокировки
del db.sqlite3-journal  # Windows
rm db.sqlite3-journal   # Linux/Mac

# Перезапустите сервер
python manage.py runserver
```

---

### Сброс базы данных

**Проблема:**
Нужно начать с чистой базы

**Решение:**
```bash
# Остановите сервер (Ctrl+C)

# Удалите базу данных
del db.sqlite3  # Windows
rm db.sqlite3   # Linux/Mac

# Примените миграции заново
python manage.py migrate

# Создайте нового суперпользователя
python manage.py createsuperuser
```

---

### Ошибка: таблица не существует

**Проблема:**
```
OperationalError: no such table: lessons_lesson
```

**Решение:**
```bash
# Примените миграции
python manage.py migrate

# Если не помогло, сделайте миграции заново
python manage.py makemigrations
python manage.py migrate
```

---

## 👥 Проблемы с пользователями

### Не могу войти в систему

**Проблема:**
Неверное имя пользователя или пароль

**Решение:**
1. Убедитесь, что аккаунт создан
2. Проверьте правильность username (не email)
3. Сбросьте пароль через Django admin
4. Создайте нового пользователя:
```bash
python manage.py createsuperuser
```

---

### Ошибка: профиль пользователя не существует

**Проблема:**
```
DoesNotExist: Profile matching query does not exist
```

**Решение:**
```python
# Профиль создается автоматически при регистрации
# Если ошибка возникла, создайте вручную через Django shell:
python manage.py shell
```
```python
from django.contrib.auth.models import User
from user.models import Profile

user = User.objects.get(username='your_username')
Profile.objects.create(user=user, level='A1', total_points=0)
```

---

### Забыли пароль администратора

**Решение:**
```bash
# Измените пароль через командную строку
python manage.py changepassword admin

# Или создайте нового суперпользователя
python manage.py createsuperuser
```

---

## ⚡ Проблемы производительности

### Сайт загружается медленно

**Решение:**
1. Проверьте количество запросов к БД
2. Используйте select_related/prefetch_related
3. Добавьте индексы в базу данных
4. Включите кэширование

---

### Большой размер базы данных

**Решение:**
```bash
# Удалите старые логи
del debug.log  # Windows
rm debug.log   # Linux/Mac

# Очистите старые сессии
python manage.py clearsessions

# Оптимизируйте базу данных (SQLite)
python manage.py shell
```
```python
from django.db import connection
cursor = connection.cursor()
cursor.execute("VACUUM")
```

---

## 🌐 Проблемы с интернет-соединением

### Ошибка: Connection refused

**Проблема:**
```
ConnectionError: HTTPSConnectionPool(host='intelligence.io.solutions', port=443)
```

**Решение:**
1. Проверьте подключение к интернету
2. Проверьте настройки прокси/VPN
3. Убедитесь, что домен доступен:
```bash
ping intelligence.io.solutions
```
4. Попробуйте изменить base_url в настройках

---

## 📝 Логирование и отладка

### Включение подробных логов

```python
# В EnglishForYou/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'DEBUG',  # Измените с INFO на DEBUG
    },
}
```

### Просмотр логов

```bash
# Windows
type debug.log

# Linux/Mac
cat debug.log
tail -f debug.log  # В реальном времени
```

---

## 🆘 Если ничего не помогло

1. **Проверьте логи:** `debug.log` в корне проекта
2. **Создайте Issue:** [GitHub Issues](https://github.com/yourusername/EnglishForYou/issues)
3. **Включите подробную информацию:**
   - Версия Python
   - Версия Django
   - Операционная система
   - Полный текст ошибки
   - Шаги для воспроизведения

---

## 📞 Получение помощи

- **GitHub Issues:** для багов
- **GitHub Discussions:** для вопросов
- **Проверьте документацию:** [README.md](README.md)

---

**Последнее обновление:** 2025-10-20
