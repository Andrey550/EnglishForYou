"""
Management command to test async lesson generation
"""
import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from lessons.services.lesson_ai_service import LessonAIService
import time


class Command(BaseCommand):
    help = 'Test async lesson generation with OpenAI'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to test with'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"Testing with user: {username}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} not found"))
            return
        
        service = LessonAIService()
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Starting async lesson generation test...")
        self.stdout.write("="*60 + "\n")
        
        # Test synchronous wrapper
        self.stdout.write("Testing synchronous wrapper...")
        start_time = time.time()
        
        try:
            block = service.generate_block(user)
            
            if block:
                elapsed_time = time.time() - start_time
                self.stdout.write(self.style.SUCCESS(f"✓ Block created successfully in {elapsed_time:.2f} seconds!"))
                self.stdout.write(f"  - Block title: {block.title}")
                self.stdout.write(f"  - Grammar topic: {block.grammar_topic}")
                self.stdout.write(f"  - Level: {block.level}")
                self.stdout.write(f"  - Difficulty: {block.difficulty_level}")
                
                lessons = block.lessons.all()
                self.stdout.write(f"\n  Lessons created: {lessons.count()}")
                for lesson in lessons:
                    self.stdout.write(f"    - {lesson.lesson_type}: {lesson.title}")
            else:
                self.stdout.write(self.style.ERROR("✗ Failed to create block"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))
        
        # Test async method directly
        self.stdout.write("\n" + "-"*60)
        self.stdout.write("Testing async method directly...")
        start_time = time.time()
        
        try:
            # Create new event loop for testing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def test_async():
                """Test async generation with timing for each operation"""
                self.stdout.write("Starting async operations...")
                
                # Collect user data
                try:
                    profile = user.profile
                except AttributeError:
                    from user.models import UserProfile
                    profile = UserProfile.objects.create(user=user)
                
                user_data = {
                    'about': profile.about or 'не указано',
                    'interests': profile.interests or 'не указано',
                    'learning_goals': profile.learning_goals or 'не указано',
                }
                
                progress_data = service.analyze_user_progress(user)
                
                # Operation 1: Generate block info
                op1_start = time.time()
                self.stdout.write("  1. Generating block info...")
                block_info = await service._generate_block_info_async(user_data, progress_data)
                op1_time = time.time() - op1_start
                
                if block_info:
                    self.stdout.write(self.style.SUCCESS(f"     ✓ Block info generated in {op1_time:.2f}s"))
                    self.stdout.write(f"       Title: {block_info.get('title')}")
                else:
                    self.stdout.write(self.style.ERROR(f"     ✗ Failed to generate block info"))
                    return None
                
                # Operations 2-4: Generate lessons in parallel
                self.stdout.write("  2-4. Generating lessons in parallel...")
                
                tasks_start = time.time()
                lesson_tasks = [
                    service._generate_grammar_lesson_async(block_info, progress_data),
                    service._generate_vocabulary_lesson_async(block_info, user_data, progress_data),
                    service._generate_reading_lesson_async(block_info, user_data, progress_data)
                ]
                
                lessons_data = await asyncio.gather(*lesson_tasks)
                tasks_time = time.time() - tasks_start
                
                if all(lessons_data):
                    self.stdout.write(self.style.SUCCESS(f"     ✓ All lessons generated in {tasks_time:.2f}s"))
                    for i, lesson in enumerate(lessons_data, 1):
                        if lesson:
                            self.stdout.write(f"       Lesson {i}: {lesson.get('lesson_type')} - {lesson.get('title')}")
                else:
                    self.stdout.write(self.style.ERROR("     ✗ Some lessons failed to generate"))
                
                return block_info, lessons_data
            
            result = loop.run_until_complete(test_async())
            elapsed_time = time.time() - start_time
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"\n✓ Async test completed in {elapsed_time:.2f} seconds total!"))
            else:
                self.stdout.write(self.style.ERROR("\n✗ Async test failed"))
            
            loop.close()
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Async test error: {str(e)}"))
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Test completed!")
        self.stdout.write("="*60)
