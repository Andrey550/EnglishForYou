"""
Файл: validators.py
Описание: Валидаторы для проверки данных уроков

Этот файл содержит функции валидации:
- validate_block_json() - проверка структуры JSON от AI (блок с 3 уроками)
- check_answer() - проверка ответов пользователя на упражнения

Валидация гарантирует корректность данных перед сохранением в БД.
"""

import json
import logging

logger = logging.getLogger(__name__)


def validate_block_json(block_data):
    """
    Валидация JSON структуры блока от AI
    
    Args:
        block_data: dict с данными блока
        
    Returns:
        tuple (is_valid: bool, error_message: str)
    """
    try:
        # Проверка обязательных полей блока
        required_fields = ['title', 'description', 'level', 'difficulty_level', 'grammar_topic', 'lessons']
        
        for field in required_fields:
            if field not in block_data:
                return False, f"Отсутствует поле: {field}"
        
        # Проверка lessons
        if not isinstance(block_data['lessons'], list):
            return False, "lessons должен быть массивом"
        
        if len(block_data['lessons']) != 3:
            return False, f"Должно быть 3 урока, получено: {len(block_data['lessons'])}"
        
        # Проверка каждого урока
        lesson_types = ['grammar', 'vocabulary', 'reading']
        for index, lesson in enumerate(block_data['lessons']):
            expected_type = lesson_types[index]
            
            if 'lesson_type' not in lesson:
                return False, f"Урок {index+1}: отсутствует lesson_type"
            
            if lesson['lesson_type'] != expected_type:
                return False, f"Урок {index+1}: ожидается {expected_type}, получено {lesson['lesson_type']}"
            
            if 'title' not in lesson:
                return False, f"Урок {index+1}: отсутствует title"
            
            if 'content' not in lesson:
                return False, f"Урок {index+1}: отсутствует content"
            
            # Проверка content
            content = lesson['content']
            
            if 'exercises' not in content:
                return False, f"Урок {index+1}: отсутствуют exercises"
            
            if not isinstance(content['exercises'], list):
                return False, f"Урок {index+1}: exercises должны быть массивом"
            
            if len(content['exercises']) != 5:
                return False, f"Урок {index+1}: должно быть 5 упражнений, получено {len(content['exercises'])}"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False, f"Ошибка валидации: {str(e)}"


def check_answer(user_answer, correct_answer):
    """
    Мягкая проверка ответа пользователя
    
    Args:
        user_answer: str или int - ответ пользователя
        correct_answer: str или int - правильный ответ
        
    Returns:
        bool
    """
    # Проверка на None
    if user_answer is None or correct_answer is None:
        return False
    
    # Для multiple_choice (индексы)
    if isinstance(correct_answer, int):
        try:
            return int(user_answer) == correct_answer
        except (ValueError, TypeError):
            return False
    
    # Для текстовых ответов
    if isinstance(user_answer, str) and isinstance(correct_answer, str):
        # Проверка на пустые строки
        if not user_answer.strip() or not correct_answer.strip():
            return False
        return user_answer.strip().lower() == correct_answer.strip().lower()
    
    # Для true/false
    if str(user_answer).lower() in ['true', 'false']:
        return str(user_answer).lower() == str(correct_answer).lower()
    
    return False
