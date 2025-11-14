#!/usr/bin/env python
"""
Complete OTP signup flow test
"""
import os
import django
import random
import string
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from quiz.models import EmailOTP

client = Client()

print("[TEST] Complete OTP Signup Flow\n")

# Generate unique username and email for each test run
random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
test_email = f'testuser{random_str}@example.com'
test_username = f'testuser{random_str}'
test_password = 'TestPass@12345'

response = client.post('/signup/', {
    'username': test_username,
    'email': test_email,
    'password1': test_password,
    'password2': test_password,
})

print(f"Status: {response.status_code}")
if response.status_code == 302:
    print("✓ Signup form accepted")
    print(f"Redirect to: {response['Location']}")
else:
    print("✗ Signup failed")
    print(response.content.decode())
    exit(1)

# Get OTP from database
otp_record = EmailOTP.objects.filter(email=test_email).latest('created_at')
otp_code = otp_record.otp

print(f"✓ OTP generated: {otp_code}")
print(f"✓ OTP valid: {otp_record.is_valid()}")

# Step 2: Verify OTP
print("\n" + "=" * 50)
print("STEP 2: OTP Verification")
print("=" * 50)

# First, get verify_otp page to check session
response = client.get('/verify-otp/')
print(f"GET /verify-otp/: {response.status_code}")

# Submit OTP verification
response = client.post('/verify-otp/', {
    'otp': otp_code,
})

print(f"Status: {response.status_code}")

if response.status_code == 302:
    print("✓ OTP verified successfully")
    print(f"Redirect to: {response['Location']}")
else:
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        # Check if there's an error in the response
        content = response.content.decode()
        if 'error' in content.lower() or 'invalid' in content.lower():
            print("✗ OTP verification failed")
            print(content[:500])
        else:
            print("Response received (may be form with errors)")
    else:
        print("✗ Unexpected status")

# Step 3: Check if user was created
print("\n" + "=" * 50)
print("STEP 3: Verify Account Creation")
print("=" * 50)

try:
    user = User.objects.get(username=test_username)
    print(f"✓ User created: {user.username}")
    print(f"✓ Email: {user.email}")
    print(f"✓ Is active: {user.is_active}")
    
    # Check if user is logged in
    response = client.get('/dashboard/')
    if response.status_code == 200:
        print("✓ User logged in (can access dashboard)")
    else:
        print(f"Dashboard access: {response.status_code}")
        
except User.DoesNotExist:
    print("✗ User was NOT created")

# Step 4: Check OTP status
print("\n" + "=" * 50)
print("STEP 4: OTP Status")
print("=" * 50)

otp_record.refresh_from_db()
print(f"OTP verified: {otp_record.is_verified}")
print(f"OTP attempts: {otp_record.attempts}")

print("\n" + "=" * 50)
print("[DONE] Complete flow test finished")
print("=" * 50)
