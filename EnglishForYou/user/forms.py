from django.contrib.auth.models import User
from django import forms

class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg text-base transition-all focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(5,150,105,0.1)] focus:-translate-y-px placeholder:text-gray-400',
                'placeholder': 'Введите ваше имя'}),
            
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg text-base transition-all focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(5,150,105,0.1)] focus:-translate-y-px placeholder:text-gray-400',
                'placeholder': 'Введите вашу фамилию'}),
            
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg text-base transition-all focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(5,150,105,0.1)] focus:-translate-y-px placeholder:text-gray-400',
                'placeholder': 'Введите ваш email'}),
            
            'password': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg text-base transition-all focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(5,150,105,0.1)] focus:-translate-y-px placeholder:text-gray-400',
                'placeholder': 'Создайте надежный пароль'}),
        }
        
class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'password']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg text-base transition-all duration-300 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(5,150,105,0.1)]',
                'placeholder': 'Введите ваш email'}),
            'password': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg text-base transition-all duration-300 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(5,150,105,0.1)]',
                'placeholder': 'Введите ваш пароль'}),
        }