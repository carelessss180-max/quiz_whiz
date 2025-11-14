#!/usr/bin/env python
"""
Test script to simulate two concurrent users trying to find a match.
Run this AFTER starting the dev server (python manage.py runserver).

Steps:
1. Create two test users (or use existing).
2. Log both users in and get session cookies.
3. Simulate concurrent calls to find-match API for the same quiz.
4. Observe server logs to see if matching happens.
"""

import os
import django
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from quiz.models import Quiz

BASE_URL = 'http://127.0.0.1:8000'

def login_and_get_session(username, password):
    """Log in a user and return the requests Session with auth cookie."""
    session = requests.Session()
    resp = session.post(
        f'{BASE_URL}/login/',
        data={'username': username, 'password': password},
        allow_redirects=True
    )
    if resp.status_code != 200:
        print(f"Login failed for {username}")
        return None
    print(f"✓ Logged in as {username}")
    return session

def find_match_api(session, quiz_id):
    """Call the api_find_match endpoint."""
    url = f'{BASE_URL}/quiz/api/find-match/{quiz_id}/'
    try:
        resp = session.get(url)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  → api_find_match response: {data}")
            return data
        else:
            print(f"  → api_find_match error: {resp.status_code}")
            return None
    except Exception as e:
        print(f"  → api_find_match exception: {e}")
        return None

def check_match_api(session, match_id):
    """Call the api_check_match endpoint."""
    url = f'{BASE_URL}/quiz/api/check-match/{match_id}/'
    try:
        resp = session.get(url)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  → api_check_match response: {data}")
            return data
        else:
            print(f"  → api_check_match error: {resp.status_code}")
            return None
    except Exception as e:
        print(f"  → api_check_match exception: {e}")
        return None

def main():
    # Create or get test users
    user1, _ = User.objects.get_or_create(username='testuser1', defaults={'email': 'testuser1@test.com'})
    user2, _ = User.objects.get_or_create(username='testuser2', defaults={'email': 'testuser2@test.com'})
    
    # Set passwords (for login)
    user1.set_password('testpass123')
    user1.save()
    user2.set_password('testpass123')
    user2.save()
    print(f"✓ Created/updated test users: {user1.username}, {user2.username}")
    
    # Get a quiz to test with
    quiz = Quiz.objects.first()
    if not quiz:
        print("✗ No quizzes found. Please create a quiz in admin first.")
        return
    print(f"✓ Using quiz: {quiz.title} (id={quiz.id})")
    
    # Log both users in
    session1 = login_and_get_session('testuser1', 'testpass123')
    session2 = login_and_get_session('testuser2', 'testpass123')
    
    if not session1 or not session2:
        print("✗ Failed to log in users")
        return
    
    print("\n" + "="*60)
    print("SCENARIO 1: Sequential calls (baseline)")
    print("="*60)
    
    # User 1 calls find_match
    print("\n[User 1] Calling api_find_match...")
    result1 = find_match_api(session1, quiz.id)
    match_id_1 = result1.get('match_id') if result1 else None
    
    # User 2 calls find_match (should claim User 1's waiting match)
    print("\n[User 2] Calling api_find_match...")
    result2 = find_match_api(session2, quiz.id)
    
    if result1 and result2:
        if result1.get('status') == 'waiting' and result2.get('status') == 'matched':
            print("\n✓ SUCCESS: User 1 created waiting match, User 2 claimed it!")
        elif result1.get('status') == 'matched' and result2.get('status') == 'matched':
            print("\n✓ SUCCESS: Both got matched!")
        else:
            print(f"\n✗ ISSUE: User 1 got '{result1.get('status')}', User 2 got '{result2.get('status')}'")
    
    print("\n" + "="*60)
    print("SCENARIO 2: Concurrent calls (the problematic case)")
    print("="*60)
    
    # Clear any existing matches for these users
    from quiz.models import Matchmaking
    from django.db.models import Q
    Matchmaking.objects.filter(
        (Q(player1__in=[user1, user2]) | Q(player2__in=[user1, user2])),
        quiz=quiz
    ).delete()
    print("✓ Cleared previous matches")
    
    print("\n[Concurrent] Both users call api_find_match simultaneously...")
    
    results = {}
    def call_find_for_user(user_name, session, quiz_id):
        print(f"  → [{user_name}] calling...")
        result = find_match_api(session, quiz_id)
        results[user_name] = result
        return result
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(call_find_for_user, 'User 1', session1, quiz.id)
        f2 = executor.submit(call_find_for_user, 'User 2', session2, quiz.id)
        f1.result()
        f2.result()
    
    print("\n[Results summary]")
    for user_name, result in results.items():
        if result:
            print(f"{user_name}: status={result.get('status')}, match_id={result.get('match_id')}")
        else:
            print(f"{user_name}: ERROR")
    
    # Check if both got the same match_id and both are in 'matched' state
    match_ids = [r.get('match_id') for r in results.values() if r and r.get('match_id')]
    statuses = [r.get('status') for r in results.values() if r]
    
    if len(match_ids) == 2 and match_ids[0] == match_ids[1] and 'matched' in statuses:
        print("\n✓ SUCCESS: Both users share same match_id and at least one is matched!")
    elif len(set(match_ids)) == 2:
        print(f"\n✗ ISSUE: Both users created separate waiting matches (IDs: {match_ids})")
        print("         This indicates atomic claiming is not working properly.")
    else:
        print(f"\n? UNCLEAR: Results = {results}")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()
