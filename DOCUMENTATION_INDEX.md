# 📚 Индекс документации EnglishForYou

Навигация по всей документации проекта.

## 🚀 Начало работы

### Для пользователей
- **[README.md](README.md)** - Главная страница проекта с полным описанием
- **[QUICK_START.md](QUICK_START.md)** - Быстрый запуск проекта за 5 минут

### Для разработчиков
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Как внести вклад в проект
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Полная API документация
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Техническая сводка проекта

## 📝 Управление проектом

- **[CHANGELOG.md](CHANGELOG.md)** - История изменений и версии
- **[LICENSE](LICENSE)** - MIT лицензия проекта

## 📸 Визуальное представление

- **[SCREENSHOTS.md](SCREENSHOTS.md)** - Скриншоты интерфейса (шаблон)

## 🔧 Конфигурация

- **[.env.example](.env.example)** - Пример файла переменных окружения
- **[requirements.txt](requirements.txt)** - Python зависимости проекта

## 📋 GitHub Templates

### Issue Templates
- **[Bug Report](.github/ISSUE_TEMPLATE/bug_report.md)** - Шаблон для сообщения об ошибках
- **[Feature Request](.github/ISSUE_TEMPLATE/feature_request.md)** - Шаблон для предложения функций

### Pull Request
- **[Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md)** - Шаблон для PR

## 📖 Структура по темам

### 🎯 Быстрый старт
1. Прочитайте [README.md](README.md) - обзор проекта
2. Следуйте [QUICK_START.md](QUICK_START.md) - установка
3. Изучите [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - архитектура

### 👨‍💻 Разработка
1. Прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) - правила
2. Изучите [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API
3. Используйте templates для Issues и PR

### 📚 Изучение кода
1. **Backend:** `EnglishForYou/lessons/` - основная логика уроков
2. **AI Service:** `EnglishForYou/lessons/services/` - генерация контента
3. **Models:** `EnglishForYou/*/models.py` - структура БД
4. **Views:** `EnglishForYou/*/views.py` - логика представлений

## 🔍 Поиск по документации

### По ключевым словам:

**Установка и настройка:**
- README.md (раздел "Установка и запуск")
- QUICK_START.md (весь файл)
- .env.example (конфигурация)

**AI и генерация уроков:**
- API_DOCUMENTATION.md (раздел "AI Service API")
- PROJECT_SUMMARY.md (раздел "AI Integration")
- README.md (раздел "Конфигурация")

**Структура проекта:**
- README.md (раздел "Структура проекта")
- PROJECT_SUMMARY.md (раздел "Модульная структура")

**API эндпоинты:**
- API_DOCUMENTATION.md (весь файл)

**Вклад в проект:**
- CONTRIBUTING.md (весь файл)
- Pull Request Template

**История и изменения:**
- CHANGELOG.md (весь файл)

## 📱 Быстрые ссылки

| Что нужно | Куда идти |
|-----------|-----------|
| Запустить проект | [QUICK_START.md](QUICK_START.md) |
| Понять архитектуру | [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) |
| Использовать API | [API_DOCUMENTATION.md](API_DOCUMENTATION.md) |
| Сообщить о баге | [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md) |
| Предложить функцию | [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md) |
| Внести изменения | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Посмотреть историю | [CHANGELOG.md](CHANGELOG.md) |

## 🎓 Обучающие материалы

### Для новичков в Django
Рекомендуем изучить в таком порядке:
1. Models (`EnglishForYou/lessons/models.py`)
2. Views (`EnglishForYou/lessons/views.py`)
3. Templates (`EnglishForYou/lessons/templates/`)
4. Services (`EnglishForYou/lessons/services/`)

### Для изучения AI интеграции
1. `lessons/services/prompts.py` - промпты для AI
2. `lessons/services/lesson_ai_service.py` - логика генерации
3. API_DOCUMENTATION.md - как использовать сервис

## ℹ️ Дополнительная информация

- **Вопросы?** Создайте Issue с меткой `question`
- **Идеи?** Используйте GitHub Discussions
- **Баги?** Используйте Bug Report Template
- **Новые функции?** Используйте Feature Request Template

---

**Последнее обновление:** 2025-10-20  
**Версия документации:** 1.0.0

---

💡 **Совет:** Добавьте этот файл в закладки для быстрого доступа ко всей документации!
