// Получение CSRF токена
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Получение ответа пользователя из упражнения
function getUserAnswer(exercise) {
  const type = exercise.dataset.type;
  
  if (type === 'fill_blank' || type === 'correct_mistake' || type === 'translate') {
    const input = exercise.querySelector('input.user-answer');
    return input ? input.value.trim() : '';
  }
  
  if (type === 'multiple_choice' || type === 'true_false') {
    const checked = exercise.querySelector('input.user-answer:checked');
    return checked ? checked.value : '';
  }
  
  return '';
}

// Обработка кнопок подсказок
document.querySelectorAll('.hint-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    const exercise = this.closest('.exercise');
    const hintDiv = exercise.querySelector('.hint');
    
    if (hintDiv) {
      // Toggle hint visibility
      if (hintDiv.classList.contains('hidden')) {
        hintDiv.classList.remove('hidden');
        this.textContent = '💡 Hide Hint';
        this.classList.add('bg-yellow-200');
      } else {
        hintDiv.classList.add('hidden');
        this.textContent = '💡 Hint';
        this.classList.remove('bg-yellow-200');
      }
    }
  });
});

// Проверка одного упражнения (AJAX)
document.querySelectorAll('.check-btn').forEach(btn => {
  btn.addEventListener('click', async function() {
    const exercise = this.closest('.exercise');
    const exerciseId = exercise.dataset.id;
    const userAnswer = getUserAnswer(exercise);
    
    // Проверка что ответ не пустой
    if (!userAnswer) {
      alert('Please select or enter an answer');
      return;
    }
    
    try {
      // AJAX запрос
      const response = await fetch('/lessons/save-progress/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          lesson_id: lessonId,
          exercise_id: exerciseId,
          user_answer: userAnswer
        })
      });
      
      const data = await response.json();
      
      // Показать результат
      const resultDiv = exercise.querySelector('.result');
      const iconSpan = resultDiv.querySelector('.icon');
      const statusText = resultDiv.querySelector('.status-text');
      const explanationDiv = resultDiv.querySelector('.explanation');
      
      resultDiv.classList.remove('hidden', 'bg-green-50', 'bg-red-50');
      
      if (data.is_correct) {
        resultDiv.classList.add('bg-green-50');
        iconSpan.textContent = '✅';
        statusText.textContent = 'Correct!';
        statusText.classList.remove('text-red-700');
        statusText.classList.add('text-green-700');
      } else {
        resultDiv.classList.add('bg-red-50');
        iconSpan.textContent = '❌';
        statusText.textContent = 'Incorrect';
        statusText.classList.remove('text-green-700');
        statusText.classList.add('text-red-700');
      }
      
      explanationDiv.textContent = data.explanation;
      
      // Заблокировать кнопку "Проверить"
      this.disabled = true;
      this.classList.add('opacity-50', 'cursor-not-allowed');
      
    } catch (error) {
      console.error('Error checking answer:', error);
      alert('Error checking answer. Please try again.');
    }
  });
});

// Завершение урока (финальное сохранение)
document.getElementById('completeBtn')?.addEventListener('click', async function() {
  const exercises = document.querySelectorAll('.exercise');
  const exercisesData = {};
  
  // Собрать все ответы
  let allAnswered = true;
  
  exercises.forEach(exercise => {
    const exerciseId = exercise.dataset.id;
    const userAnswer = getUserAnswer(exercise);
    const correctAnswer = exercise.dataset.answer;
    
    if (!userAnswer) {
      allAnswered = false;
      return;
    }
    
    // Проверка ответа на клиенте (для подсчёта)
    let isCorrect = false;
    
    if (exercise.dataset.type === 'multiple_choice' || exercise.dataset.type === 'true_false') {
      isCorrect = (userAnswer == correctAnswer);
    } else {
      isCorrect = (userAnswer.toLowerCase() === correctAnswer.toLowerCase());
    }
    
    exercisesData[exerciseId] = {
      answer: userAnswer,
      is_correct: isCorrect
    };
  });
  
  // Проверка что все упражнения выполнены
  if (!allAnswered) {
    alert('⚠️ Please complete all exercises before finishing the lesson');
    return;
  }
  
  // Заблокировать кнопку
  this.disabled = true;
  this.textContent = 'Saving...';
  
  try {
    // AJAX запрос на завершение
    const response = await fetch('/lessons/complete-lesson/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({
        lesson_id: lessonId,
        exercises: exercisesData
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Показать модальное окно с результатом
      showResultModal(data);
    } else {
      alert('❌ ' + (data.error || 'Error saving lesson'));
      this.disabled = false;
      this.textContent = '✅ Complete Lesson';
    }
    
  } catch (error) {
    console.error('Error completing lesson:', error);
    alert('❌ Network error. Please try again.');
    this.disabled = false;
    this.textContent = '✅ Complete Lesson';
  }
});

// Показать модальное окно результата
function showResultModal(data) {
  const modal = document.getElementById('resultModal');
  const icon = document.getElementById('resultIcon');
  const title = document.getElementById('resultTitle');
  const score = document.getElementById('resultScore');
  const message = document.getElementById('resultMessage');
  const nextBtn = document.getElementById('nextLessonBtn');
  
  // Установить значения
  score.textContent = data.score + '%';
  
  if (data.score >= 80) {
    icon.textContent = '🎉';
    title.textContent = 'Lesson Complete!';
    message.textContent = data.message;
    score.classList.remove('text-red-600');
    score.classList.add('text-green-600');
    
    // Показать кнопку "Следующий урок" если есть
    if (data.next_lesson_unlocked) {
      nextBtn.classList.remove('hidden');
      nextBtn.onclick = () => location.reload();
    }
  } else {
    icon.textContent = '😕';
    title.textContent = 'Try Again';
    message.textContent = data.message;
    score.classList.remove('text-green-600');
    score.classList.add('text-red-600');
    nextBtn.classList.add('hidden');
  }
  
  // Показать модальное окно
  modal.classList.remove('hidden');
  
  // Закрытие по клику вне окна
  modal.addEventListener('click', function(e) {
    if (e.target === modal) {
      modal.classList.add('hidden');
    }
  });
}
