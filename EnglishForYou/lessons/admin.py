from django.contrib import admin
from .models import LessonBlock, Lesson, LessonProgress


@admin.register(LessonBlock)
class LessonBlockAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order', 'title', 'level', 'difficulty_level', 'is_completed', 'is_passed', 'completion_percent', 'created_at']
    list_filter = ['level', 'difficulty_level', 'is_completed', 'is_passed']
    search_fields = ['title', 'user__username', 'grammar_topic']
    ordering = ['user', 'order']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'block', 'order', 'lesson_type', 'title', 'is_unlocked', 'estimated_time']
    list_filter = ['lesson_type', 'is_unlocked']
    search_fields = ['title', 'block__title']
    ordering = ['block', 'order']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'lesson', 'best_score', 'current_score', 'is_completed', 'attempts', 'last_accessed']
    list_filter = ['is_completed', 'lesson__lesson_type']
    search_fields = ['user__username', 'lesson__title']
    ordering = ['-last_accessed']
