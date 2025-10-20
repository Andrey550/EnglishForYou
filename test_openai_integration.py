"""
Simple test script for OpenAI integration
"""
import os
import sys
import django

# Add the project directory to path
sys.path.insert(0, 'D:\\EnglishForYou\\EnglishForYou')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EnglishForYou.settings')
django.setup()

import asyncio
import time
from django.contrib.auth.models import User
from lessons.services.lesson_ai_service import LessonAIService


def test_openai_connection():
    """Test if OpenAI connection works"""
    print("Testing OpenAI connection...")
    
    service = LessonAIService()
    test_prompt = "Say 'Hello World' in JSON format with a key 'message'"
    
    try:
        response = service._call_openai(test_prompt, max_tokens=50)
        if response:
            print("✓ OpenAI connection successful!")
            print(f"Response: {response[:100]}...")
            return True
        else:
            print("✗ No response from OpenAI")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False


def test_sync_generation():
    """Test synchronous lesson generation"""
    print("\n" + "="*60)
    print("Testing synchronous lesson generation...")
    print("="*60)
    
    try:
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        
        if created:
            print(f"Created test user: {user.username}")
        else:
            print(f"Using existing user: {user.username}")
        
        service = LessonAIService()
        
        print("\nStarting lesson block generation...")
        start_time = time.time()
        
        block = service.generate_block(user)
        
        elapsed_time = time.time() - start_time
        
        if block:
            print(f"\n✓ Block created successfully in {elapsed_time:.2f} seconds!")
            print(f"  - Block ID: {block.id}")
            print(f"  - Title: {block.title}")
            print(f"  - Grammar Topic: {block.grammar_topic}")
            print(f"  - Level: {block.level}")
            print(f"  - Difficulty: {block.difficulty_level}/5")
            print(f"  - Description: {block.description[:100]}...")
            
            lessons = block.lessons.all()
            print(f"\n  Lessons created: {lessons.count()}")
            for lesson in lessons:
                print(f"    - Lesson {lesson.order}: {lesson.lesson_type} - {lesson.title}")
                exercises = lesson.content.get('exercises', [])
                print(f"      Exercises: {len(exercises)}")
            
            return True
        else:
            print(f"✗ Failed to create block after {elapsed_time:.2f} seconds")
            return False
            
    except Exception as e:
        print(f"✗ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_generation():
    """Test async lesson generation"""
    print("\n" + "="*60)
    print("Testing asynchronous lesson generation...")
    print("="*60)
    
    try:
        # Get test user
        user = User.objects.get(username='test_user')
        print(f"Using user: {user.username}")
        
        service = LessonAIService()
        
        # Prepare data
        try:
            profile = user.profile
        except:
            from user.models import UserProfile
            profile = UserProfile.objects.create(user=user)
        
        user_data = {
            'about': profile.about or 'Software developer interested in technology',
            'interests': profile.interests or 'Programming, AI, Technology',
            'learning_goals': profile.learning_goals or 'Business English'
        }
        
        progress_data = service.analyze_user_progress(user)
        print(f"User level: {progress_data['level']}, Difficulty: {progress_data['difficulty']}")
        
        # Test async operations
        print("\nOperation 1: Generating block info...")
        start_time = time.time()
        
        block_info = await service._generate_block_info_async(user_data, progress_data)
        
        op1_time = time.time() - start_time
        
        if block_info:
            print(f"✓ Block info generated in {op1_time:.2f}s")
            print(f"  Title: {block_info.get('title')}")
            print(f"  Topic: {block_info.get('grammar_topic')}")
        else:
            print(f"✗ Failed to generate block info")
            return False
        
        print("\nOperations 2-4: Generating lessons in parallel...")
        tasks_start = time.time()
        
        # Create lesson tasks
        lesson_tasks = [
            service._generate_grammar_lesson_async(block_info, progress_data),
            service._generate_vocabulary_lesson_async(block_info, user_data, progress_data),
            service._generate_reading_lesson_async(block_info, user_data, progress_data)
        ]
        
        # Wait for all tasks
        lessons_data = await asyncio.gather(*lesson_tasks)
        
        tasks_time = time.time() - tasks_start
        
        print(f"✓ All lessons generated in parallel in {tasks_time:.2f}s")
        
        for i, lesson in enumerate(lessons_data, 1):
            if lesson:
                print(f"  Lesson {i}: {lesson.get('lesson_type')} - {lesson.get('title')}")
                exercises = lesson.get('content', {}).get('exercises', [])
                print(f"    Exercises: {len(exercises)}")
            else:
                print(f"  Lesson {i}: Failed to generate")
        
        total_time = op1_time + tasks_time
        print(f"\nTotal async generation time: {total_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during async generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("="*60)
    print("OpenAI Integration Test Suite")
    print("="*60)
    
    # Test 1: Connection
    if not test_openai_connection():
        print("\n⚠ OpenAI connection failed. Check your API key and network.")
        return
    
    # Test 2: Sync generation
    if not test_sync_generation():
        print("\n⚠ Synchronous generation failed.")
        return
    
    # Test 3: Async generation
    print("\nRunning async test...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(test_async_generation())
        if success:
            print("\n✅ All tests passed successfully!")
        else:
            print("\n⚠ Async generation test failed.")
    finally:
        loop.close()
    
    print("\n" + "="*60)
    print("Test suite completed!")
    print("="*60)


if __name__ == "__main__":
    main()
