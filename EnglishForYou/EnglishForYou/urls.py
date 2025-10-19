from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', include('main.urls')),
    path('user/', include('user.urls')),
    path('test/', include('user_test.urls')),  
    path('lessons/', include('lessons.urls')),  # 👈 Добавить
]
