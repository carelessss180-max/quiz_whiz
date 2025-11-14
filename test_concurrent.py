from django.contrib.auth.models import User
from django.db.models import Q
from quiz.models import Quiz, Matchmaking, UserProfile
from django.utils import timezone
import time
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

# Get or create test users
user1, _ = User.objects.get_or_create(username='testuser1', defaults={'email': 'testuser1@test.com'})
user2, _ = User.objects.get_or_create(username='testuser2', defaults={'email': 'testuser2@test.com'})
user1.set_password('testpass123')
user1.save()
user2.set_password('testpass123')
user2.save()

print(f"✓ Created/updated test users: {user1.username}, {user2.username}")

# Ensure both users have profiles and are marked online
profile1, _ = UserProfile.objects.get_or_create(user=user1)
profile2, _ = UserProfile.objects.get_or_create(user=user2)
profile1.save()  # This triggers auto_now and marks them as recently active
profile2.save()
print(f"✓ User profiles created/updated (marked online)")

# Get a quiz
quiz = Quiz.objects.first()
if not quiz:
    print("✗ No quizzes found.")
else:
    print(f"✓ Using quiz: {quiz.title} (id={quiz.id})")
    
    # Clear previous matches for these users
    Matchmaking.objects.filter(
        (Q(player1__in=[user1, user2]) | Q(player2__in=[user1, user2])),
        quiz=quiz
    ).delete()
    print("✓ Cleared previous matches")
    
    print("\n" + "="*60)
    print("CONCURRENT MATCHING TEST")
    print("="*60)
    
    results = {}
    
    def simulate_find_match(user, user_name):
        """Simulate the find_match logic from views.py"""
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        
        # Check if user already in a match
        existing_match = Matchmaking.objects.filter(
            Q(player1=user) | Q(player2=user),
            quiz=quiz,
            status__in=['waiting', 'in_progress']
        ).first()
        
        if existing_match:
            results[user_name] = {'status': 'has_existing', 'match_id': str(existing_match.id)}
            print(f"  [{user_name}] Found existing match: {existing_match.id}")
            return
        
        # Look for waiting matches to claim
        waiting_matches = Matchmaking.objects.filter(
            quiz=quiz,
            player2__isnull=True,
            status='waiting',
            created_at__gte=five_minutes_ago
        ).exclude(player1=user).order_by('created_at')
        
        print(f"  [{user_name}] Found {waiting_matches.count()} candidate waiting matches")
        
        for waiting_match in waiting_matches:
            try:
                player1_profile = UserProfile.objects.get(user=waiting_match.player1)
            except UserProfile.DoesNotExist:
                print(f"  [{user_name}] Deleting match {waiting_match.id} (no profile)")
                waiting_match.delete()
                continue
            
            if (timezone.now() - player1_profile.last_activity) >= timedelta(minutes=5):
                print(f"  [{user_name}] Deleting match {waiting_match.id} (player offline)")
                waiting_match.delete()
                continue
            
            # Try to claim the match atomically
            print(f"  [{user_name}] Attempting to claim match {waiting_match.id}...")
            updated = Matchmaking.objects.filter(pk=waiting_match.pk, player2__isnull=True).update(
                player2=user,
                status='in_progress'
            )
            
            if updated:
                results[user_name] = {'status': 'matched', 'match_id': str(waiting_match.id)}
                print(f"  [{user_name}] ✓ Successfully claimed match {waiting_match.id}")
                return
            else:
                print(f"  [{user_name}] ✗ Failed to claim (already claimed)")
        
        # Create new waiting match
        new_match = Matchmaking.objects.create(quiz=quiz, player1=user, status='waiting')
        results[user_name] = {'status': 'created_waiting', 'match_id': str(new_match.id)}
        print(f"  [{user_name}] Created new waiting match: {new_match.id}")
    
    print("\nCalling find_match concurrently for both users...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(simulate_find_match, user1, 'User 1')
        f2 = executor.submit(simulate_find_match, user2, 'User 2')
        f1.result()
        f2.result()
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    for user_name, result in results.items():
        print(f"{user_name}: {result}")
    
    # Check outcome
    statuses = [r['status'] for r in results.values()]
    match_ids = [r['match_id'] for r in results.values()]
    
    if len(set(match_ids)) == 1:
        print("\n✓ SUCCESS: Both users share the SAME match_id!")
        if 'matched' in statuses:
            print("✓ SUCCESS: At least one user successfully claimed the match!")
    else:
        print(f"\n✗ PROBLEM: Both users created SEPARATE matches: {match_ids}")
        print("   This means the atomic claiming is not preventing race conditions.")
