#!/usr/bin/env python
"""
Simple HTTP test using curl-like approach
"""
import subprocess
import re

BASE_URL = "http://127.0.0.1:8000"

print("[1] Testing server connection...")
result = subprocess.run(['curl', '-I', f'{BASE_URL}/'], capture_output=True, text=True)
if result.returncode == 0:
    print("✓ Server is running")
else:
    print(f"✗ Server connection failed: {result.stderr}")
    exit(1)

print("\n[2] Getting signup page...")
result = subprocess.run(['curl', '-s', f'{BASE_URL}/signup/'], capture_output=True, text=True)

# Extract CSRF token
match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', result.stdout)
if match:
    csrf_token = match.group(1)
    print(f"✓ CSRF token: {csrf_token[:20]}...")
else:
    print("✗ CSRF token not found")
    exit(1)

print("\n[3] Submitting signup form...")
form_data = (
    f"username=testuser999&"
    f"email=testuser999@gmail.com&"
    f"password1=Test@12345!&"
    f"password2=Test@12345!&"
    f"csrfmiddlewaretoken={csrf_token}"
)

result = subprocess.run(
    ['curl', '-s', '-i', '-X', 'POST',
     f'{BASE_URL}/signup/',
     '-d', form_data],
    capture_output=True,
    text=True
)

print("Response:")
print(result.stdout[:500])

# Check for redirect
if '302' in result.stdout or 'Location' in result.stdout:
    print("\n✓ Form submitted successfully!")
else:
    print("\n✗ Form submission may have failed")
