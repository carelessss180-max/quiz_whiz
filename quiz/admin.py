# quiz/admin.py
from django.contrib import admin
from .models import Quiz, Question, Choice, QuizResult

# This helps display choices directly under questions in the admin panel
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3 # Show 3 empty choice fields by default

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'time_limit') # <-- Correct indentation

admin.site.register(Quiz)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(QuizResult)