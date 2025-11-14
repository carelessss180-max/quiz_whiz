#!/usr/bin/env python
"""
Test signup flow directly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.contrib.auth.models import User
from quiz.models import EmailOTP
from quiz.forms import SignupForm
from django.core.mail import send_mail

# Simulate form submission
print("[TEST] Simulating signup form submission...")

# Create form data
form_data = {
    'username': 'testuser123',
    'email': 'testuser@gmail.com',
    'password1': 'Test@12345!',
    'password2': 'Test@12345!',
}

# Validate form
form = SignupForm(form_data)
print(f"Form valid: {form.is_valid()}")

if not form.is_valid():
    print(f"Form errors: {form.errors}")
    for field, errors in form.errors.items():
        print(f"  {field}: {errors}")
else:
    print("[SUCCESS] Form is valid!")
    
    # Get cleaned data
    email = form.cleaned_data['email']
    username = form.cleaned_data['username']
    password = form.cleaned_data['password1']
    
    print(f"\nEmail: {email}")
    print(f"Username: {username}")
    
    # Create OTP
    print("\n[STEP 1] Creating OTP...")
    otp_obj = EmailOTP.create_otp(email)
    print(f"✓ OTP: {otp_obj.otp}")
    
    # Send email
    print("\n[STEP 2] Sending email...")
    try:
        send_mail(
            subject='QuizWhiz - Email Verification OTP',
            message=f'Your OTP for QuizWhiz signup is: {otp_obj.otp}\n\nThis OTP is valid for 10 minutes.',
            from_email='noreply@quizwhiz.com',
            recipient_list=[email],
            fail_silently=False,
        )
        print("✓ Email sent!")
    except Exception as e:
        print(f"✗ Email failed: {e}")

print("\n[DONE]")
