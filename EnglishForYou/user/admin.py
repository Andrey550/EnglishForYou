from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Дополнительная информация'
    
    # Группируем поля для удобства
    fieldsets = (
        ('Личная информация', {
            'fields': ('about', 'interests', 'learning_goals', 'language_level')
        }),
        ('Статистика', {
            'fields': ('days_streak', 'words_learned', 'lessons_completed', 'last_activity')
        }),
    )


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


# Перерегистрируем User модель с новым админом
admin.site.unregister(User)
admin.site.register(User, UserAdmin)