#!/usr/bin/env python
"""
Direct test by calling Django view directly 
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.test import Client

# Create test client
client = Client()

print("[TEST] Direct signup test")

# POST to signup directly
print("\n[POST] Submitting signup form...")
response = client.post('/signup/', {
    'username': 'directtest123',
    'email': 'directtest@example.com',
    'password1': 'Test@12345!',
    'password2': 'Test@12345!',
})

print(f"Status Code: {response.status_code}")

if response.status_code == 302:
    print("✓ Form accepted! (302 redirect)")
    print(f"Redirected to: {response['Location']}")
elif response.status_code == 200:
    print("✓ Form displayed with status 200")
else:
    print(f"Status: {response.status_code}")
    
print("\n[DONE]")
