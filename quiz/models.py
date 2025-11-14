import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# --- USER PROFILE FOR ONLINE STATUS ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    last_activity = models.DateTimeField(auto_now=True, help_text="Last activity timestamp")
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True, help_text="User profile photo")
    bio = models.CharField(max_length=500, blank=True, null=True, help_text="Short bio about the user")
    
    def __str__(self):
        return f"{self.user.username} - Profile"
    
    @property
    def is_online(self):
        """Check if user is online (active within last 5 minutes)"""
        from datetime import timedelta
        return (timezone.now() - self.last_activity) < timedelta(minutes=5)

# --- STEP 1: 'Quiz' CLASS SABSE PEHLE AANI CHAHIYE ---
class Quiz(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    is_featured = models.BooleanField(default=False, help_text="Show in Latest Quizzes section")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

# --- STEP 2: 'Question' CLASS ISKE BAAD AAYEGI ---
class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    time_limit = models.IntegerField(default=15, help_text="Time limit for this question in seconds")

    def __str__(self):
        return self.text

# --- STEP 3: 'Choice' CLASS ISKE BAAD AAYEGI ---
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    # Short explanation or brief answer displayed in results (editable via admin)
    explanation = models.TextField(null=True, blank=True, help_text="Brief explanation or answer shown on results page")

    def __str__(self):
        return f"{self.question.text[:50]} - {self.text}"

# --- STEP 4: 'QuizResult' CLASS ISKE BAAD AAYEGI ---
class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    # Store user's selected answers as a JSON mapping: {question_id: choice_id}
    selected_answers = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - Score: {self.score}"

# --- STEP 5: 'Challenge' CLASS AAKHIR MEIN AAYEGI ---
# (Kyonki isko 'Quiz' aur 'User' dono ki zaroorat hai)
class Challenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    
    challenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="challenges_started")
    challenger_score = models.IntegerField()
    
    opponent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="challenges_received", null=True, blank=True)
    opponent_score = models.IntegerField(null=True, blank=True)
    
    STATUS_CHOICES = [
        ('waiting', 'Waiting for opponent'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Challenge {self.id} for {self.quiz.title}"

# --- STEP 6: 'Matchmaking' CLASS FOR AUTO-MATCHMAKING ---
class Matchmaking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='matchmakings')
    
    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches_as_player1")
    player1_score = models.IntegerField(null=True, blank=True)
    
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches_as_player2", null=True, blank=True)
    player2_score = models.IntegerField(null=True, blank=True)
    
    STATUS_CHOICES = [
        ('waiting', 'Waiting for player 2'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Match {self.id}: {self.quiz.title}"

# --- USER ACHIEVEMENTS & BADGES ---
class Badge(models.Model):
    BADGE_TYPES = [
        ('10_wins', '10 Wins'),
        ('50_wins', '50 Wins'),
        ('100_wins', '100 Wins'),
        ('perfect_score', 'Perfect Score'),
        ('streak_3', '3-Quiz Streak'),
        ('streak_10', '10-Quiz Streak'),
        ('all_difficulties', 'Master of All'),
        ('speed_demon', 'Speed Demon'),
        ('comeback_king', 'Comeback King'),
    ]
    
    badge_type = models.CharField(max_length=20, unique=True, choices=BADGE_TYPES)
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Icon name for badge (e.g., trophy, star, bolt)")
    color = models.CharField(max_length=20, default='warning', choices=[
        ('success', 'Green'),
        ('primary', 'Blue'),
        ('danger', 'Red'),
        ('warning', 'Yellow'),
        ('info', 'Cyan'),
        ('dark', 'Dark'),
    ])
    
    class Meta:
        ordering = ['badge_type']
    
    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


# --- SOCIAL FEATURES ---
class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
        ]
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class ShareableResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_results')
    quiz_result = models.ForeignKey(QuizResult, on_delete=models.CASCADE, related_name='shares')
    shared_at = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=500, blank=True, null=True, help_text="Custom message with result")
    is_public = models.BooleanField(default=True, help_text="Visible on user's profile")
    views_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-shared_at']
    
    def __str__(self):
        return f"{self.user.username} shared {self.quiz_result.quiz.title}"


# --- NOTIFICATIONS ---
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_quiz', 'New Quiz Added'),
        ('badge_earned', 'Badge Earned'),
        ('challenge_received', 'Challenge Received'),
        ('result_shared', 'Result Shared'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"