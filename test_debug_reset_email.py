#!/usr/bin/env python
"""
Debug Password Reset Email Sending
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from quiz.models import PasswordReset
from django.core.mail import EmailMultiAlternatives

print("[DEBUG] Testing Password Reset Email Sending\n")

# Create test user
try:
    user = User.objects.create_user(
        username='debugtest123',
        email='debugtest123@example.com',
        password='TestPass@12345'
    )
    print(f"✓ Created user: {user.username} ({user.email})")
except:
    user = User.objects.get(username='debugtest123')
    print(f"✓ User exists: {user.username} ({user.email})")

# Create reset token
print("\n" + "="*50)
print("Creating Password Reset Token")
print("="*50)

reset_obj = PasswordReset.create_reset(user)
print(f"✓ Token created: {reset_obj.token[:30]}...")
print(f"✓ Is valid: {reset_obj.is_valid()}")

# Manually send email (simulating what forgot_password view does)
print("\n" + "="*50)
print("Sending Reset Email")
print("="*50)

from django.urls import reverse

# Build reset link
reset_link = f"http://127.0.0.1:8000/reset-password/{reset_obj.token}/"

html_message = f"""
<html>
    <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #333;">Reset Your Password 🔐</h2>
            <p style="color: #666; font-size: 16px;">Hi {user.first_name or user.username},</p>
            
            <p style="color: #666;">We received a request to reset your password. Click the button below to set a new password:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="display: inline-block; background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
            </div>
            
            <p style="color: #999; font-size: 13px;">This link is valid for 24 hours. If you didn't request this, please ignore this email.</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">QuizWhiz © 2024</p>
        </div>
    </body>
</html>
"""

try:
    msg = EmailMultiAlternatives(
        subject='QuizWhiz - Password Reset Request',
        body=f'Click this link to reset your password: {reset_link}',
        from_email='noreply@quizwhiz.com',
        to=[user.email]
    )
    msg.attach_alternative(html_message, "text/html")
    result = msg.send(fail_silently=False)
    
    print(f"✓ Email send result: {result}")
    print(f"✓ Sent to: {user.email}")
    print(f"✓ Reset link: {reset_link}")
    print("\n[SUCCESS] Email should arrive in Gmail inbox!")
    
except Exception as e:
    print(f"✗ Error sending email: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Next Steps:")
print("="*50)
print("1. Check Gmail inbox for reset email")
print("2. Click the reset link")
print("3. Enter new password")
print("4. Login with new password")
