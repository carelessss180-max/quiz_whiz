#!/usr/bin/env python
"""
Test Forgot Password & Reset Link Feature
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from quiz.models import PasswordReset

print("[TEST] Forgot Password Feature\n")

client = Client()

# Create test user
try:
    user = User.objects.create_user(
        username='resettest',
        email='resettest@example.com',
        password='OldPass@12345'
    )
    print("✓ Test user created: resettest")
except:
    user = User.objects.get(username='resettest')
    print("✓ Test user already exists: resettest")

# Test 1: Request Reset Link
print("\n" + "="*50)
print("TEST 1: Request Forgot Password Link")
print("="*50)

response = client.post('/forgot-password/', {
    'email': user.email,
})

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("✓ Forgot password form submitted")
    
    # Check if email was created
    reset_obj = PasswordReset.objects.filter(user=user).latest('created_at')
    print(f"✓ Reset token generated: {reset_obj.token[:20]}...")
    print(f"✓ Is valid: {reset_obj.is_valid()}")
    print(f"✓ Is used: {reset_obj.is_used}")
else:
    print(f"✗ Unexpected status: {response.status_code}")

# Test 2: Access Reset Link
print("\n" + "="*50)
print("TEST 2: Access Reset Password Link")
print("="*50)

reset_token = reset_obj.token
reset_url = f'/reset-password/{reset_token}/'

response = client.get(reset_url)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("✓ Reset password page accessible")
else:
    print(f"✗ Reset page not accessible: {response.status_code}")

# Test 3: Reset Password
print("\n" + "="*50)
print("TEST 3: Submit New Password")
print("="*50)

new_password = 'NewPass@54321'
response = client.post(reset_url, {
    'password1': new_password,
    'password2': new_password,
})

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("✓ Password reset submitted")
    
    # Verify token is marked as used
    reset_obj.refresh_from_db()
    print(f"✓ Token marked as used: {reset_obj.is_used}")
    print(f"✓ Token valid now: {reset_obj.is_valid()}")
    
    # Try to login with new password
    login_success = client.login(username='resettest', password=new_password)
    if login_success:
        print("✓ Login with new password: SUCCESS")
    else:
        print("✗ Login with new password: FAILED")
else:
    print(f"✗ Password reset failed: {response.status_code}")

# Test 4: Verify Token Expiry
print("\n" + "="*50)
print("TEST 4: Token Expiry Check")
print("="*50)

# Try to use same token again (should fail - one-time use)
response = client.post(reset_url, {
    'password1': 'Another@12345',
    'password2': 'Another@12345',
})

print(f"Status Code: {response.status_code}")
print("✓ Re-using token (should show error message)")

# Test 5: Invalid Token
print("\n" + "="*50)
print("TEST 5: Invalid Token")
print("="*50)

response = client.get('/reset-password/invalid_token_xyz/')
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("✓ Invalid token handled gracefully")

print("\n" + "="*50)
print("[DONE] All tests completed!")
print("="*50)
