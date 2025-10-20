"""views.py - Представления для работы с пользователями.

Этот файл содержит все view-функции для регистрации, авторизации,
выхода из системы и отображения профиля пользователя.
"""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, RegisterForm
from user_test.models import TestSession

User = get_user_model()


# Список доступных интересов для выбора
AVAILABLE_INTERESTS = [
    'Спорт', 'Музыка', 'Кино', 'Путешествия', 'Технологии',
    'Наука', 'Искусство', 'Литература', 'Кулинария', 'Бизнес'
]


# Страница регистрации нового пользователя
def register_view(request):
    # Обработка POST-запроса с данными регистрации
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Получаем данные из формы
            username = form.cleaned_data['username']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Создаем нового пользователя
            user = User.objects.create_user(
                username=username,
                first_name=username,
                last_name=last_name,
                email=email,
                password=password
            )
            # Автоматически входим после регистрации
            login(request, user)
            return redirect('/')

        # Если форма не валидна, показываем ошибки
        return render(request, 'user/register.html', {'form': form})

    # GET-запрос - показываем пустую форму
    return render(request, 'user/register.html', {'form': RegisterForm()})


# Страница входа в систему
def login_view(request):
    # Обработка POST-запроса с данными входа
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Получаем email и пароль из формы
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Ищем пользователя по email
            user_obj = User.objects.filter(email=email).first()
            if user_obj:
                # Проверяем пароль через authenticate
                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    # Вход успешен
                    login(request, user)
                    return redirect('/')

        # Если данные не верны, показываем форму с ошибками
        return render(request, 'user/login.html', {'form': form})

    # GET-запрос - показываем пустую форму
    return render(request, 'user/login.html', {'form': LoginForm()})


# Выход из системы
def logout_view(request):
    logout(request)
    return redirect('/')


# Страница профиля пользователя (только для авторизованных)
@login_required(login_url='login')
def user_profile_view(request):
    user = request.user
    
    # Проверяем существование профиля и создаем если нет
    try:
        profile = user.profile
    except:
        # Создаем профиль если его нет
        from user.models import Profile
        profile = Profile.objects.create(user=user)
    
    # Обработка POST-запроса - сохранение данных профиля
    if request.method == 'POST':
        # Получаем данные из формы
        interests = request.POST.get('interests', '')
        goals = request.POST.get('goals', '')
        about = request.POST.get('about', '')
        
        # Сохраняем данные в профиль
        profile.set_interests_list([x.strip() for x in interests.split(',') if x.strip()])
        profile.set_goals_list([x.strip() for x in goals.split(',') if x.strip()])
        profile.about = about.strip()
        profile.save()
        
        return redirect('user_profile')
    
    # Получаем последний пройденный тест для определения уровня
    last_test = TestSession.objects.filter(
        user=user,
        status__in=['completed', 'timeout']
    ).order_by('-completed_at').first()
    
    # Обновляем уровень языка в профиле на основе теста
    if last_test and last_test.determined_level:
        if profile.language_level != last_test.determined_level:
            profile.language_level = last_test.determined_level
            profile.save()
    
    # Подготавливаем данные для отображения в шаблоне
    context = {
        'interests_list': profile.get_interests_list(),
        'goals_list': profile.get_goals_list(),
        'available_interests': AVAILABLE_INTERESTS,
        'recent_activities': profile._normalize_csv_to_list(profile.last_activity)[:5],
        'language_level': profile.language_level,
        'last_test': last_test,
    }
    
    return render(request, 'user/user_profile.html', context)