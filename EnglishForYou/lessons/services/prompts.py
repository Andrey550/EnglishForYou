def build_block_info_prompt(user_data, progress_data):
    """
    Построение промпта для генерации информации о блоке (название и темы)
    
    Args:
        user_data: dict с данными пользователя
        progress_data: dict с данными прогресса
    Returns:
        str: промпт для генерации информации о блоке
    """
    
    # Формирование списка пройденных тем
    covered_topics_str = ', '.join(progress_data.get('covered_topics', [])) if progress_data.get('covered_topics') else 'нет'
    
    prompt = f"""Создай информацию о блоке из 3 уроков для изучения английского языка.

ПОЛЬЗОВАТЕЛЬ:
- Уровень: {progress_data.get('level', 'A1')}
- Сложность блока: {progress_data.get('difficulty', 1)}/5
- Пройдено успешных блоков: {progress_data.get('passed_blocks', 0)}
- О себе: {user_data.get('about', 'не указано')}
- Интересы: {user_data.get('interests', 'не указано')}
- Цели: {user_data.get('learning_goals', 'не указано')}

РЕЗУЛЬТАТЫ ТЕСТА:
- Грамматика: {progress_data.get('grammar_score', 0)}%
- Лексика: {progress_data.get('vocabulary_score', 0)}%
- Чтение: {progress_data.get('reading_score', 0)}%

ПРОЙДЕННЫЕ ТЕМЫ (не повторять):
{covered_topics_str}

ЗАДАЧА:
Создай общую информацию о блоке уроков для изучения английского.
1. Выбери НОВУЮ грамматическую тему уровня {progress_data.get('level', 'A1')}, которая НЕ была в пройденных темах
2. Придумай интересное название блока
3. Создай описание блока
4. Определи уровень и сложность

ФОРМАТ JSON:
{{
  "title": "Present Simple",
  "description": "Изучение настоящего простого времени для описания повседневных действий и привычек",
  "level": "{progress_data.get('level', 'A1')}",
  "difficulty_level": {progress_data.get('difficulty', 1)},
  "grammar_topic": "present_simple"
}}

Вернуть ТОЛЬКО валидный JSON без markdown блоков!"""
    
    return prompt


def build_grammar_lesson_prompt(block_info, progress_data):
    """
    Построение промпта для генерации урока грамматики
    
    Args:
        block_info: dict с информацией о блоке
        progress_data: dict с данными прогресса
    Returns:
        str: промпт для генерации урока грамматики
    """
    
    difficulty = progress_data.get('difficulty', 1)
    difficulty_params = {
        1: 'простые, очевидные ответы',
        2: 'простые',
        3: 'средние',
        4: 'средние, неочевидные ответы',
        5: 'сложные, требуют размышления'
    }
    
    exercise_difficulty = difficulty_params.get(difficulty, 'простые')
    
    prompt = f"""Создай урок грамматики по теме "{block_info['title']}".

ТЕМА: {block_info['grammar_topic']}
УРОВЕНЬ: {block_info['level']}
СЛОЖНОСТЬ УПРАЖНЕНИЙ: {exercise_difficulty}

ТРЕБОВАНИЯ:
1. Объясни правило понятно и с примерами
2. Создай РОВНО 5 разнообразных упражнений
3. Используй разные типы упражнений: fill_blank, multiple_choice, correct_mistake
4. Каждое упражнение должно иметь объяснение правильного ответа

СТРУКТУРА JSON:
{{
  "lesson_type": "grammar",
  "title": "Название урока грамматики",
  "content": {{
    "rule": {{
      "title": "{block_info['title']}",
      "explanation": "Детальное объяснение правила на русском языке...",
      "examples": [
        "I work every day",
        "She likes coffee",
        "They don't play tennis"
      ]
    }},
    "exercises": [
      {{
        "id": "ex1",
        "type": "fill_blank",
        "question": "She ___ (work) in a bank.",
        "correct_answer": "works",
        "explanation": "3rd person singular + s"
      }},
      {{
        "id": "ex2",
        "type": "multiple_choice",
        "question": "They ___ to school every day.",
        "options": ["go", "goes", "going", "went"],
        "correct_answer": 0,
        "explanation": "Plural subject + base form"
      }},
      // ... еще 3 упражнения
    ]
  }}
}}

Вернуть ТОЛЬКО валидный JSON без markdown блоков!"""
    
    return prompt


def build_vocabulary_lesson_prompt(block_info, user_data, progress_data):
    """
    Построение промпта для генерации урока лексики
    
    Args:
        block_info: dict с информацией о блоке
        user_data: dict с данными пользователя
        progress_data: dict с данными прогресса
    Returns:
        str: промпт для генерации урока лексики
    """
    
    difficulty = progress_data.get('difficulty', 1)
    word_counts = {1: 10, 2: 12, 3: 13, 4: 15, 5: 18}
    num_words = word_counts.get(difficulty, 10)
    
    prompt = f"""Создай урок лексики, связанный с темой "{block_info['title']}".

ИНТЕРЕСЫ ПОЛЬЗОВАТЕЛЯ: {user_data.get('interests', 'не указано')}
УРОВЕНЬ: {block_info['level']}
КОЛИЧЕСТВО СЛОВ: {num_words}

ТРЕБОВАНИЯ:
1. Подбери {num_words} слов, связанных с грамматической темой и интересами пользователя
2. Для каждого слова дай перевод и пример использования
3. Создай РОВНО 5 упражнений на закрепление лексики
4. Используй разные типы: translate, fill_blank, matching

СТРУКТУРА JSON:
{{
  "lesson_type": "vocabulary",
  "title": "Vocabulary: {block_info['title']}",
  "content": {{
    "words": [
      {{
        "word": "technology",
        "translation": "технология",
        "example": "Modern technology changes our lives."
      }},
      // ... еще {num_words - 1} слов
    ],
    "exercises": [
      {{
        "id": "ex1",
        "type": "translate",
        "question": "Переведи: технология",
        "correct_answer": "technology",
        "explanation": "Правильный перевод"
      }},
      {{
        "id": "ex2",
        "type": "fill_blank",
        "question": "Modern ___ changes our lives.",
        "correct_answer": "technology",
        "explanation": "Используем новое слово"
      }},
      // ... еще 3 упражнения
    ]
  }}
}}

Вернуть ТОЛЬКО валидный JSON без markdown блоков!"""
    
    return prompt


def build_reading_lesson_prompt(block_info, user_data, progress_data):
    """
    Построение промпта для генерации урока чтения
    
    Args:
        block_info: dict с информацией о блоке
        user_data: dict с данными пользователя
        progress_data: dict с данными прогресса
    Returns:
        str: промпт для генерации урока чтения
    """
    
    difficulty = progress_data.get('difficulty', 1)
    text_lengths = {1: 200, 2: 250, 3: 300, 4: 350, 5: 400}
    text_length = text_lengths.get(difficulty, 200)
    
    prompt = f"""Создай урок чтения, используя грамматику "{block_info['title']}".

ИНТЕРЕСЫ ПОЛЬЗОВАТЕЛЯ: {user_data.get('interests', 'не указано')}
ЦЕЛИ ОБУЧЕНИЯ: {user_data.get('learning_goals', 'не указано')}
УРОВЕНЬ: {block_info['level']}
ДЛИНА ТЕКСТА: ~{text_length} слов

ТРЕБОВАНИЯ:
1. Напиши интересный текст на {text_length} слов по интересам пользователя
2. Активно используй изучаемую грамматическую конструкцию "{block_info['grammar_topic']}"
3. Создай глоссарий из 5-7 сложных слов
4. Создай РОВНО 5 вопросов на понимание текста
5. Используй разные типы: multiple_choice, true_false, short_answer

СТРУКТУРА JSON:
{{
  "lesson_type": "reading",
  "title": "Reading: {block_info['title']} in Context",
  "content": {{
    "text": "Текст на {text_length} слов на английском языке, который активно использует {block_info['grammar_topic']}...",
    "glossary": [
      {{
        "word": "innovative",
        "translation": "инновационный"
      }},
      // ... еще 4-6 слов
    ],
    "exercises": [
      {{
        "id": "ex1",
        "type": "multiple_choice",
        "question": "What is the main idea of the text?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": 0,
        "explanation": "Объяснение правильного ответа"
      }},
      {{
        "id": "ex2",
        "type": "true_false",
        "question": "The author mentions technology in the text.",
        "correct_answer": "true",
        "explanation": "Это упоминается в параграфе 2"
      }},
      // ... еще 3 вопроса
    ]
  }}
}}

Вернуть ТОЛЬКО валидный JSON без markdown блоков!"""
    
    return prompt


def build_lesson_block_prompt(user_data, progress_data):
    """
    Построение промпта для генерации блока уроков
    
    Args:
        user_data: dict с данными пользователя (profile, interests, goals, etc.)
        progress_data: dict с данными прогресса (level, difficulty, covered_topics, test_scores)
    """
    
    # Параметры по сложности
    difficulty_params = {
        1: {
            'vocabulary_words': 10,
            'reading_length': 200,
            'grammar_complexity': 'базовые правила',
            'exercise_difficulty': 'простые, очевидные ответы'
        },
        2: {
            'vocabulary_words': 12,
            'reading_length': 250,
            'grammar_complexity': 'простые правила',
            'exercise_difficulty': 'простые'
        },
        3: {
            'vocabulary_words': 13,
            'reading_length': 300,
            'grammar_complexity': 'средние правила',
            'exercise_difficulty': 'средние'
        },
        4: {
            'vocabulary_words': 15,
            'reading_length': 350,
            'grammar_complexity': 'продвинутые правила',
            'exercise_difficulty': 'средние, неочевидные ответы'
        },
        5: {
            'vocabulary_words': 18,
            'reading_length': 400,
            'grammar_complexity': 'самые сложные правила уровня',
            'exercise_difficulty': 'сложные, требуют размышления'
        }
    }
    
    difficulty = progress_data.get('difficulty', 1)
    params = difficulty_params.get(difficulty, difficulty_params[1])
    
    # Формирование списка пройденных тем
    covered_topics_str = ', '.join(progress_data.get('covered_topics', [])) if progress_data.get('covered_topics') else 'нет'
    
    prompt = f"""Создай блок из 3 уроков для изучения английского языка.

ПОЛЬЗОВАТЕЛЬ:
- Уровень: {progress_data.get('level', 'A1')}
- Сложность блока: {difficulty}/5
- Пройдено успешных блоков: {progress_data.get('passed_blocks', 0)}
- О себе: {user_data.get('about', 'не указано')}
- Интересы: {user_data.get('interests', 'не указано')}
- Цели: {user_data.get('learning_goals', 'не указано')}

РЕЗУЛЬТАТЫ ТЕСТА:
- Грамматика: {progress_data.get('grammar_score', 0)}%
- Лексика: {progress_data.get('vocabulary_score', 0)}%
- Чтение: {progress_data.get('reading_score', 0)}%

ПРОЙДЕННЫЕ ТЕМЫ (не повторять):
{covered_topics_str}

ПАРАМЕТРЫ:
- Грамматика: {params['grammar_complexity']}
- Лексика: {params['vocabulary_words']} слов по интересам пользователя
- Чтение: текст ~{params['reading_length']} слов по интересам пользователя
- Упражнения: {params['exercise_difficulty']}

ТРЕБОВАНИЯ:
1. Выбери НОВУЮ грамматическую тему уровня {progress_data.get('level', 'A1')}
2. Создай 3 урока в строгом порядке:
   - Урок 1: Грамматика (правило + примеры + 5 упражнений)
   - Урок 2: Лексика ({params['vocabulary_words']} слов + 5 упражнений)
   - Урок 3: Чтение (текст {params['reading_length']} слов + глоссарий 5-7 слов + 5 вопросов)

3. СТРУКТУРА УРОКА 1 (ГРАММАТИКА):
{{
  "lesson_type": "grammar",
  "title": "Название урока",
  "content": {{
    "rule": {{
      "title": "Present Simple",
      "explanation": "Детальное объяснение правила...",
      "examples": [
        "I work every day",
        "She likes coffee",
        "They don't play tennis"
      ]
    }},
    "exercises": [
      {{
        "id": "ex1",
        "type": "fill_blank",
        "question": "She ___ (work) in a bank.",
        "correct_answer": "works",
        "explanation": "3rd person singular + s"
      }},
      {{
        "id": "ex2",
        "type": "multiple_choice",
        "question": "They ___ to school every day.",
        "options": ["go", "goes", "going", "went"],
        "correct_answer": 0,
        "explanation": "Plural subject + base form"
      }},
      {{
        "id": "ex3",
        "type": "correct_mistake",
        "question": "He don't like pizza.",
        "correct_answer": "doesn't",
        "explanation": "3rd person singular uses doesn't"
      }},
      {{
        "id": "ex4",
        "type": "fill_blank",
        "question": "We ___ (not/eat) meat.",
        "correct_answer": "don't eat",
        "explanation": "Negative form with plural subject"
      }},
      {{
        "id": "ex5",
        "type": "multiple_choice",
        "question": "___ you speak English?",
        "options": ["Do", "Does", "Are", "Is"],
        "correct_answer": 0,
        "explanation": "Question with plural 'you'"
      }}
    ]
  }}
}}

4. СТРУКТУРА УРОКА 2 (ЛЕКСИКА):
{{
  "lesson_type": "vocabulary",
  "title": "Название урока",
  "content": {{
    "words": [
      {{
        "word": "technology",
        "translation": "технология",
        "example": "Modern technology changes our lives."
      }},
      // ... ещё {params['vocabulary_words'] - 1} слов
    ],
    "exercises": [
      {{
        "id": "ex1",
        "type": "translate",
        "question": "Переведи: технология",
        "correct_answer": "technology",
        "explanation": "Правильный перевод"
      }},
      {{
        "id": "ex2",
        "type": "fill_blank",
        "question": "Modern ___ changes our lives.",
        "correct_answer": "technology",
        "explanation": "Вставляем новое слово"
      }},
      // ... ещё 3 упражнения (всего 5)
    ]
  }}
}}

5. СТРУКТУРА УРОКА 3 (ЧТЕНИЕ):
{{
  "lesson_type": "reading",
  "title": "Название урока",
  "content": {{
    "text": "Текст на {params['reading_length']} слов по интересам пользователя...",
    "glossary": [
      {{
        "word": "innovative",
        "translation": "инновационный"
      }},
      // ... ещё 4-6 слов
    ],
    "exercises": [
      {{
        "id": "ex1",
        "type": "multiple_choice",
        "question": "What is the main idea of the text?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": 0,
        "explanation": "Объяснение"
      }},
      {{
        "id": "ex2",
        "type": "true_false",
        "question": "The text mentions modern technology.",
        "correct_answer": "true",
        "explanation": "Это упоминается в тексте"
      }},
      // ... ещё 3 вопроса (всего 5)
    ]
  }}
}}

ФОРМАТ JSON:
{{
  "title": "Present Simple",
  "description": "Изучение настоящего простого времени",
  "level": "{progress_data.get('level', 'A1')}",
  "difficulty_level": {difficulty},
  "grammar_topic": "present_simple",
  "lessons": [
    // Урок 1 (грамматика),
    // Урок 2 (лексика),
    // Урок 3 (чтение)
  ]
}}

КРИТИЧНО: 
- Вернуть ТОЛЬКО валидный JSON без markdown блоков (без ```json)!
- Все упражнения должны быть разными и проверять понимание материала
- Лексика и чтение должны быть связаны с интересами пользователя
- Объяснения должны быть понятными и краткими"""

    return prompt
