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
