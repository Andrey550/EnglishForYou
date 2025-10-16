from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, RegisterForm

User = get_user_model()

# Статический список интересов (редактируй по необходимости)
AVAILABLE_INTERESTS = [
    'Спорт', 'Музыка', 'Кино', 'Путешествия', 'Технологии',
    'Наука', 'Искусство', 'Литература', 'Кулинария', 'Бизнес'
]


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = User.objects.create_user(
                username=username,
                first_name=username,  # при желании поменяй на реальное имя
                last_name=last_name,
                email=email,
                password=password
            )
            login(request, user)
            return redirect('/')

        # вернуть форму с ошибками
        return render(request, 'user/register.html', {'form': form})

    return render(request, 'user/register.html', {'form': RegisterForm()})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user_obj = User.objects.filter(email=email).first()
            if user_obj:
                # authenticate ожидает username (строку), а не объект User
                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('/')

        # вернуть форму с ошибками
        return render(request, 'user/login.html', {'form': form})

    return render(request, 'user/login.html', {'form': LoginForm()})


def logout_view(request):
    logout(request)
    return redirect('/')


@login_required(login_url='login')
def user_profile_view(request):
    user = request.user
    profile = user.profile

    def normalize_csv(s: str) -> str:
        if not s:
            return ''
        s = s.replace('|', ',')
        items = [x.strip() for x in s.split(',') if x.strip()]
        return ','.join(items)

    def csv_to_list(s: str):
        if not s:
            return []
        s = s.replace('|', ',')
        return [x.strip() for x in s.split(',') if x.strip()]

    if request.method == 'POST':
        interests = request.POST.get('interests', '')
        goals = request.POST.get('goals', '')
        about = request.POST.get('about', '')

        profile.interests = normalize_csv(interests)
        profile.learning_goals = normalize_csv(goals)
        profile.about = about.strip()
        profile.save()

        return redirect('user_profile')

    context = {
        'interests_list': profile.get_interests_list(),
        'goals_list': profile.get_goals_list(),
        'available_interests': AVAILABLE_INTERESTS,  # твоя константа
        'recent_activities': csv_to_list(profile.last_activity)[:5],  # <= новые данные
    }
    return render(request, 'user/user_profile.html', context)