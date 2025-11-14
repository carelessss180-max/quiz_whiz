#!/usr/bin/env python
"""
Manual test of the signup endpoint using requests library
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Get CSRF token from signup page
print("[1] Getting CSRF token...")
response = requests.get(f"{BASE_URL}/signup/")
print(f"Status: {response.status_code}")

# Extract CSRF token
from bs4 import BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')
csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})

if csrf_input:
    csrf_token = csrf_input.get('value')
    print(f"✓ CSRF token found: {csrf_token[:20]}...")
else:
    print("✗ CSRF token NOT found!")
    print("HTML snippet:")
    print(response.text[:500])
    exit(1)

# Submit signup form
print("\n[2] Submitting signup form...")
signup_data = {
    'username': 'testuser999',
    'email': 'testuser999@gmail.com',
    'password1': 'Test@12345!',
    'password2': 'Test@12345!',
    'csrfmiddlewaretoken': csrf_token,
}

response = requests.post(
    f"{BASE_URL}/signup/",
    data=signup_data,
    allow_redirects=False
)

print(f"Status: {response.status_code}")
print(f"Location: {response.headers.get('Location', 'N/A')}")

if response.status_code == 302:
    print("✓ Form submitted successfully (redirected)")
else:
    print("Form response:")
    print(response.text[:500])
