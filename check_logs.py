"""
Скрипт для проверки последних логов Django
"""
import os

log_file = r"D:\EnglishForYou\EnglishForYou\debug.log"

if os.path.exists(log_file):
    print("Последние 50 строк из debug.log:")
    print("="*60)
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-50:]:
            print(line.rstrip())
else:
    print(f"Лог файл не найден: {log_file}")
    print("\nПроверьте настройки логирования в settings.py")
