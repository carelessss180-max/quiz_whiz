#!/usr/bin/env python
"""
Test SMTP connection with Mailtrap
"""
import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

host = os.environ.get('EMAIL_HOST')
port = int(os.environ.get('EMAIL_PORT', 2525))
username = os.environ.get('EMAIL_HOST_USER')
password = os.environ.get('EMAIL_HOST_PASSWORD')

print(f"Host: {host}")
print(f"Port: {port}")
print(f"Username: {username}")
print(f"Password: {password[:10]}..." if password else "Password: None")

try:
    print("\n[SMTP] Attempting connection...")
    server = smtplib.SMTP(host, port, timeout=10)
    server.set_debuglevel(1)
    print("✓ Connected to server")
    
    print("\n[SMTP] Sending EHLO...")
    server.ehlo()
    print("✓ EHLO successful")
    
    print("\n[SMTP] Starting TLS...")
    server.starttls()
    print("✓ TLS started")
    
    print("\n[SMTP] Logging in...")
    server.login(username, password)
    print("✓ Login successful")
    
    print("\n[SMTP] Sending test email...")
    from_addr = 'noreply@quizwhiz.com'
    to_addr = 'test@example.com'
    
    message = f"""From: {from_addr}
To: {to_addr}
Subject: Test Email from Mailtrap

This is a test email to verify Mailtrap SMTP connection.
OTP: 123456
"""
    
    server.sendmail(from_addr, to_addr, message)
    print("✓ Email sent successfully!")
    
    server.quit()
    print("\n✓ All tests passed!")
    
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
