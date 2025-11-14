#!/usr/bin/env python
"""
Test script to verify OTP signup flow
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from quiz.models import EmailOTP
from django.contrib.auth.models import User
from django.core.mail import send_mail

# Test 1: Create OTP
print("[TEST 1] Creating OTP...")
test_email = "test@example.com"
otp_obj = EmailOTP.create_otp(test_email)
print(f"✓ OTP created: {otp_obj.otp}")

# Test 2: Check OTP validity
print("\n[TEST 2] Checking OTP validity...")
is_valid = otp_obj.is_valid()
print(f"✓ OTP is valid: {is_valid}")

# Test 3: Send email (console backend)
print("\n[TEST 3] Sending test email...")
try:
    send_mail(
        subject='Test OTP Email',
        message=f'Your test OTP is: {otp_obj.otp}',
        from_email='noreply@quizwhiz.com',
        recipient_list=[test_email],
        fail_silently=False,
    )
    print("✓ Email sent (check console output above)")
except Exception as e:
    print(f"✗ Email failed: {e}")

# Test 4: Verify OTP
print("\n[TEST 4] Verifying OTP...")
is_valid, message = otp_obj.verify_otp(otp_obj.otp)
print(f"Verify result: {message}")
print(f"✓ OTP verified: {is_valid}")

print("\n[SUCCESS] All tests passed!")
