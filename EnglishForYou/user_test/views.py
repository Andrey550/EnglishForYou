from django.shortcuts import render

def user_test_intro_view(request):
    return render(request, 'user_test/user_test_intro.html')