# quiz/models.py
from django.db import models
from django.contrib.auth.models import User

# Blueprint for a Quiz Topic
class Quiz(models.Model):
    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=100)

    def __str__(self):
        return self.title

# Blueprint for a Question
class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)

    def __str__(self):
        return self.text

# Blueprint for a Choice/Option for a Question
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question.text[:50]} - {self.text}"

# Blueprint to store a user's result for a quiz
class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - Score: {self.score}"