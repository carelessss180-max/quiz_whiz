#!/usr/bin/env python
"""
Test all new features
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from quiz.models import EmailNotification, PasswordReset

print("[TEST] Testing New Features\n")

# Create test user
try:
    user = User.objects.create_user(
        username='featuretest',
        email='featuretest@example.com',
        password='TestPass@12345'
    )
    print("✓ Test user created")
except:
    user = User.objects.get(username='featuretest')
    print("✓ Test user already exists")

# Test 1: Password Reset
print("\n" + "="*50)
print("TEST 1: Password Reset Feature")
print("="*50)

reset_obj = PasswordReset.create_reset(user)
print(f"✓ Password reset token created: {reset_obj.token[:10]}...")
print(f"✓ Is valid: {reset_obj.is_valid()}")
print(f"✓ Is used: {reset_obj.is_used}")

# Test 2: Email Notifications
print("\n" + "="*50)
print("TEST 2: Email Notifications")
print("="*50)

from quiz.models import Quiz, QuizResult

# Create test quiz and result
quiz = Quiz.objects.first()
if quiz:
    result = QuizResult.objects.create(
        user=user,
        quiz=quiz,
        score=8,
        selected_answers={}
    )
    print(f"✓ Test quiz result created: Score {result.score}")
    
    # Test quiz result email
    email_notif = EmailNotification.create_quiz_result_email(user, result)
    print(f"✓ Quiz result email created")
    print(f"  - Type: {email_notif.email_type}")
    print(f"  - Sent: {email_notif.is_sent}")
else:
    print("⚠ No quiz found for testing")

print("\n" + "="*50)
print("[DONE] All feature tests completed!")
print("="*50)
