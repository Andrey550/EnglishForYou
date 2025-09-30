from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render
from .forms import LoginForm, RegisterForm

User = get_user_model()

def register_view(request):
    data = {'form': RegisterForm()}
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
        
            user = User.objects.create_user(username=username, first_name=username , last_name=last_name, email=email, password=password)
            user.save()
            login(request, user=user)
            
            return redirect('/')
    else:
        return render(request, 'user/register.html', data)



def login_view(request):
    data = {'form': LoginForm()}
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        User = get_user_model()
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            print(f'{email}\n{password}')
                  
            if User.objects.filter(email=email).exists():
                user = User.objects.filter(email=email).first()
                user = authenticate(request, username=user, password=password)
                
                if user is not None:
                    login(request, user=user)
                    return redirect('/')
        return render(request, 'user/login.html', data)
    else:  
        return render(request, 'user/login.html', data)
    
    
def logout_view(request):
    logout(request)
    return redirect('/')
