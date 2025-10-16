from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Дополнительная информация'
    fields = ('about',)
    
    # Важно! Это позволит создавать профиль автоматически
    def get_or_create_profile(self, obj):
        return Profile.objects.get_or_create(user=obj)


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


# Перерегистрируем User модель с новым админом
admin.site.unregister(User)
admin.site.register(User, UserAdmin)