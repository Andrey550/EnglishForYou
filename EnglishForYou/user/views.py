from django.shortcuts import render

def register_view(request):
    return render(request, 'user/register.html')

def login_view(request):
    return render(request, 'user/login.html')