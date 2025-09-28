from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Quiz, Question, QuizResult, Choice

# Home page view - lists all available quizzes
def home(request):
    quizzes = Quiz.objects.all()
    return render(request, 'quiz/home.html', {'quizzes': quizzes})

# Sign up view
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'quiz/signup.html', {'form': form})

# Login view
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'quiz/login.html', {'form': form})

# Logout view
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')

# Quiz detail view - handles both displaying the quiz and submitting answers
@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    # This block handles the form submission after the quiz is completed by JavaScript
    if request.method == 'POST':
        score = 0
        questions = quiz.questions.all()
        for question in questions:
            selected_choice_id = request.POST.get(f'question_{question.id}')
            if selected_choice_id:
                try:
                    selected_choice = get_object_or_404(Choice, pk=selected_choice_id)
                    if selected_choice.is_correct:
                        score += 1
                except (ValueError, Choice.DoesNotExist):
                    # Ignore if the choice_id is invalid or not found
                    continue

        QuizResult.objects.create(user=request.user, quiz=quiz, score=score)
        return redirect('quiz_result', quiz_id=quiz.id)

    # This block prepares the data for the JavaScript-powered quiz interface
    questions = list(quiz.questions.all())
    questions_data = []
    for question in questions:
        choices_data = []
        for choice in question.choices.all():
            choices_data.append({'id': choice.id, 'text': choice.text})
        
        questions_data.append({
            'id': question.id,
            'text': question.text,
            'choices': choices_data,
            'time_limit': question.time_limit
        })
    
    # Pass the data to the template
    context = {
        'quiz': quiz,
        'questions_data': questions_data
    }
    return render(request, 'quiz/quiz_detail.html', context)


# Quiz result view
@login_required
def quiz_result(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    # Get the latest result for this user and quiz
    result = QuizResult.objects.filter(user=request.user, quiz=quiz).latest('timestamp')
    total_questions = quiz.questions.count()
    return render(request, 'quiz/quiz_result.html', {'result': result, 'quiz': quiz, 'total_questions': total_questions})

# User dashboard view
@login_required
def dashboard(request):
    results = QuizResult.objects.filter(user=request.user).order_by('-timestamp')
    total_quizzes_taken = results.count()
    return render(request, 'quiz/dashboard.html', {'results': results, 'total_quizzes_taken': total_quizzes_taken})

# Leaderboard view
def leaderboard(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    # Get all results for this quiz, ordered by score (highest first) and then by time (earliest first)
    results = QuizResult.objects.filter(quiz=quiz).order_by('-score', 'timestamp')
    return render(request, 'quiz/leaderboard.html', {'quiz': quiz, 'results': results})