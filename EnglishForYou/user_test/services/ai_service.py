"""
AI Service для генерации вопросов через OpenRouter API
"""
import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenRouterAIService:
    """Сервис для генерации вопросов через OpenRouter API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.model = getattr(settings, 'AI_MODEL', 'tngtech/deepseek-r1t2-chimera:free')
        self.api_url = 'https://openrouter.ai/api/v1/chat/completions'
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY не установлен в settings.py")
    
    def generate_question(self, level, topic=None, question_type='single', avoid_topics=None):
        """
        Генерирует вопрос через OpenRouter API
        
        Args:
            level: Уровень сложности (A1, A2, B1, B2, C1, C2)
            topic: Тема вопроса (опционально)
            question_type: Тип вопроса (single, multiple, text)
            avoid_topics: Список тем, которые нужно избегать
        
        Returns:
            dict: Данные вопроса в формате JSON
        """
        if not self.api_key:
            raise Exception("OpenRouter API key not configured")
        
        # Формируем промпт
        prompt = self._build_prompt(level, topic, question_type, avoid_topics)
        
        try:
            # Отправляем запрос к OpenRouter API
            response = self._call_api(prompt)
            
            # Парсим ответ
            question_data = self._parse_response(response)
            
            # Валидация данных
            self._validate_question_data(question_data)
            
            logger.info(f"Успешно сгенерирован вопрос уровня {level}, тип {question_type}")
            return question_data
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопроса: {str(e)}")
            raise
    
    def _build_prompt(self, level, topic, question_type, avoid_topics):
        """Формирует промпт для AI"""
        
        # Описание уровней CEFR
        level_descriptions = {
            'A1': 'Начальный уровень - глагол to be, Present Simple, базовые слова (100-200 слов)',
            'A2': 'Элементарный - Past Simple, Future Simple, повседневная лексика (500-1000 слов)',
            'B1': 'Средний - Present Perfect, модальные глаголы, условные предложения 1-го типа',
            'B2': 'Выше среднего - Past Perfect, условные 2-3 типа, пассивный залог, идиомы',
            'C1': 'Продвинутый - сложные конструкции, редкие слова, нюансы языка',
            'C2': 'Профессиональный - уровень носителя, тонкости, сленг, архаизмы'
        }
        
        # Описание типов вопросов
        type_instructions = {
            'single': 'Один правильный ответ из 4 вариантов. correct_answer: число 0-3',
            'multiple': 'Несколько правильных ответов из 4-5 вариантов. correct_answer: массив [0,2]',
            'text': 'Текстовый ответ. correct_answer: массив возможных вариантов ["went","go"]'
        }
        
        prompt = f"""Create ONE English test question.

Parameters:
- CEFR Level: {level} ({level_descriptions.get(level, '')})
- Question type: {question_type}
- {type_instructions[question_type]}
{f'- Topic: {topic}' if topic else ''}
{f'- Avoid topics: {", ".join(avoid_topics)}' if avoid_topics else ''}

Requirements:
1. Question must match {level} level exactly
2. Use "___" for gaps in text
3. Answers must be plausible (not too obvious)
4. Explanation must be brief and clear

Response format (JSON only, no markdown):
{{
  "question_text": "What ___ your name?",
  "question_type": "{question_type}",
  "options": ["is", "are", "am", "be"],
  "correct_answer": 0,
  "explanation": "We use 'is' with singular nouns",
  "level": "{level}",
  "topic_code": "verb_to_be",
  "difficulty_score": 50
}}

CRITICAL: Return ONLY valid JSON. No markdown, no comments, no extra text!"""
        
        return prompt
    
    def _call_api(self, prompt):
        """Отправляет запрос к OpenRouter API"""
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://englishforyou.com',
            'X-Title': 'EnglishForYou Level Test'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 5000,  # Увеличено с 1000 до 2000
            'temperature': 0.7,
        }
        
        logger.info(f"Отправка запроса к OpenRouter API (модель: {self.model})")
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"Получен ответ от API: status={response.status_code}")
        
        # Логируем тело ответа для отладки
        try:
            response_json = response.json()
            # logger.debug(f"Ответ API: {json.dumps(response_json, indent=2)}")
        except:
            logger.error(f"Не удалось распарсить ответ как JSON. Тело ответа: {response.text[:500]}")
        
        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            raise Exception(f"OpenRouter API returned status {response.status_code}: {response.text[:200]}")
        
        return response.json()
    
    def _parse_response(self, response):
        """Парсит ответ от API и извлекает JSON"""
        
        try:
            # Проверяем структуру ответа
            if 'choices' not in response:
                logger.error(f"Нет 'choices' в ответе API: {response}")
                raise Exception("Invalid API response structure: missing 'choices'")
            
            if not response['choices']:
                logger.error(f"Пустой массив 'choices' в ответе API: {response}")
                raise Exception("Invalid API response: empty 'choices' array")
            
            # Получаем текст ответа
            choice = response['choices'][0]
            
            if 'message' not in choice:
                logger.error(f"Нет 'message' в choice: {choice}")
                raise Exception("Invalid API response structure: missing 'message'")
            
            if 'content' not in choice['message']:
                logger.error(f"Нет 'content' в message: {choice['message']}")
                raise Exception("Invalid API response structure: missing 'content'")
            
            content = choice['message']['content']
            
            # Проверяем, был ли ответ обрезан
            finish_reason = choice.get('finish_reason', '')
            if finish_reason == 'length':
                logger.error("AI вернул пустой контент. Причина: length")
                raise Exception("AI не смог завершить ответ из-за лимита токенов. Попробуйте другую модель или увеличьте max_tokens.")
            
            if not content or not content.strip():
                logger.error(f"AI вернул пустой контент. Finish reason: {finish_reason}")
                raise Exception(f"AI returned empty content. Finish reason: {finish_reason}")
            
            # logger.info(f"Полученный контент от AI (первые 200 символов): {content[:200]}...")
            
            # Убираем возможные markdown обёртки
            content = content.strip()
            
            # Убираем ```json и ```
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            
            if content.endswith('```'):
                content = content[:-3]
            
            content = content.strip()
            
            # logger.info(f"Очищенный контент (первые 200 символов): {content[:200]}...")
            
            # Парсим JSON
            question_data = json.loads(content)
            
            logger.info(f"Успешно распарсен JSON: {question_data}")
            
            return question_data
            
        except (KeyError, IndexError) as e:
            logger.error(f"Ошибка структуры ответа API: {str(e)}")
            logger.error(f"Полный ответ: {json.dumps(response, indent=2)}")
            raise Exception(f"Invalid API response structure: {str(e)}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {str(e)}")
            logger.error(f"Проблемный контент: {content}")
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
    
    def _validate_question_data(self, data):
        """Валидирует данные вопроса"""
        
        required_fields = ['question_text', 'question_type', 'correct_answer', 'level']
        
        for field in required_fields:
            if field not in data:
                raise Exception(f"Отсутствует обязательное поле: {field}")
        
        # Проверка типа вопроса
        if data['question_type'] not in ['single', 'multiple', 'text']:
            raise Exception(f"Неверный тип вопроса: {data['question_type']}")
        
        # Проверка вариантов ответов для single/multiple
        if data['question_type'] in ['single', 'multiple']:
            if 'options' not in data or not isinstance(data['options'], list):
                raise Exception("Для single/multiple вопросов нужен массив options")
            
            if len(data['options']) < 2:
                raise Exception("Должно быть минимум 2 варианта ответа")
        
        # Проверка формата correct_answer
        if data['question_type'] == 'single':
            if not isinstance(data['correct_answer'], int):
                # Пытаемся преобразовать
                try:
                    data['correct_answer'] = int(data['correct_answer'])
                except:
                    raise Exception("Для single вопроса correct_answer должен быть числом")
        
        elif data['question_type'] == 'multiple':
            if not isinstance(data['correct_answer'], list):
                raise Exception("Для multiple вопроса correct_answer должен быть массивом")
        
        elif data['question_type'] == 'text':
            if not isinstance(data['correct_answer'], list):
                # Если пришла строка, делаем массив
                data['correct_answer'] = [data['correct_answer']]
        
        # Проверка уровня
        valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        if data['level'] not in valid_levels:
            raise Exception(f"Неверный уровень: {data['level']}")
        
        # Установка значений по умолчанию
        if 'explanation' not in data:
            data['explanation'] = ''
        
        if 'topic_code' not in data:
            data['topic_code'] = 'general'
        
        if 'difficulty_score' not in data:
            data['difficulty_score'] = 50
        
        return data


# Синглтон для переиспользования
_ai_service_instance = None

def get_ai_service():
    """Возвращает синглтон AI сервиса"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = OpenRouterAIService()
    return _ai_service_instance