import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Quiz, Question, QuizResult, Choice, Challenge, Matchmaking, Badge, UserAchievement, UserFollow, ShareableResult, UserProfile, Notification
from .forms import UserProfileForm, UserBasicForm
from django.db.models import Q, Count, Avg, F
from django.http import HttpResponseForbidden, JsonResponse, FileResponse
from django.utils import timezone
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Home page view - show only difficulty-based quizzes (not featured)
def home(request):
    quizzes = Quiz.objects.filter(is_featured=False)
    return render(request, 'quiz/home.html', {'quizzes': quizzes})

# Latest quizzes view - show featured quizzes
def latest_quizzes(request):
    quizzes = Quiz.objects.filter(is_featured=True).order_by('-created_at')
    return render(request, 'quiz/latest_quizzes.html', {'quizzes': quizzes})

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

# User dashboard view
@login_required
def dashboard(request):
    results = QuizResult.objects.filter(user=request.user).order_by('-timestamp')
    total_quizzes_taken = results.count()
    return render(request, 'quiz/dashboard.html', {'results': results, 'total_quizzes_taken': total_quizzes_taken})

# Quiz detail view - handles quiz display and submission
@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    # Check if this is part of a Head-to-Head challenge
    challenge_id = request.GET.get('challenge_id', None)

    if request.method == 'POST':
        score = 0
        questions = quiz.questions.all()
        # Save selected answers as mapping question_id (string) -> choice_id (int)
        selected_answers = {}
        for question in questions:
            selected_choice_id = request.POST.get(f'question_{question.id}')
            # store as string key for JSON consistency
            selected_answers[str(question.id)] = int(selected_choice_id) if selected_choice_id else None
            if selected_choice_id:
                try:
                    selected_choice = get_object_or_404(Choice, pk=selected_choice_id)
                    if selected_choice.is_correct:
                        score += 1
                except (ValueError, Choice.DoesNotExist):
                    continue
        
        QuizResult.objects.create(user=request.user, quiz=quiz, score=score, selected_answers=selected_answers)
        
        # Check and award badges
        check_and_award_badges(request.user)

        # --- H2H Challenge Logic ---
        if challenge_id:
            try:
                challenge = Challenge.objects.get(id=challenge_id)
                if request.user == challenge.challenger:
                    return redirect('challenge_result', challenge_id=challenge.id)
            except Challenge.DoesNotExist:
                pass

        # --- AI Challenge Logic ---
        is_ai_challenge = request.GET.get('challenge') == 'true'
        if is_ai_challenge:
            total_questions = questions.count()
            ai_correct_answers = round(total_questions * 0.75)
            ai_score = ai_correct_answers + random.choice([-1, 0, 0, 1])
            ai_score = max(0, min(total_questions, ai_score))
            
            result_url = reverse('quiz_result', args=[quiz.id])
            return redirect(f'{result_url}?ai_score={ai_score}&challenge=true')
        
        # --- Regular quiz redirect ---
        return redirect('quiz_result', quiz_id=quiz.id)

    # --- GET Request Logic (to display the quiz) ---
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
    
    context = {
        'quiz': quiz,
        'questions_data': questions_data
    }
    return render(request, 'quiz/quiz_detail.html', context)

# Quiz result view
@login_required
def quiz_result(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    result = QuizResult.objects.filter(user=request.user, quiz=quiz).latest('timestamp')
    total_questions = quiz.questions.count()
    
    # Check if this is from robot challenge
    is_robot_challenge = request.GET.get('challenge') == 'true'
    
    ai_score_str = request.GET.get('ai_score', None)
    ai_score = int(ai_score_str) if ai_score_str is not None else None
    
    # Only generate AI score if from robot challenge
    if is_robot_challenge and ai_score is None:
        ai_correct_answers = round(total_questions * 0.75)
        ai_score = ai_correct_answers + random.choice([-1, 0, 0, 1])
        ai_score = max(0, min(total_questions, ai_score))
    
    # Calculate accuracy percentage
    accuracy = (result.score / total_questions * 100) if total_questions > 0 else 0
    
    # Prepare user's answers for rendering
    answered_questions = []
    selected_map = result.selected_answers or {}
    for question in quiz.questions.all():
        qid = str(question.id)
        sel_id = selected_map.get(qid)
        selected_choice = None
        if sel_id is not None:
            try:
                selected_choice = Choice.objects.get(pk=sel_id)
            except Choice.DoesNotExist:
                selected_choice = None
        correct_choice = question.choices.filter(is_correct=True).first()
        answered_questions.append({
            'question': question,
            'selected': selected_choice,
            'correct': correct_choice,
            'is_correct': selected_choice.is_correct if selected_choice else False
        })

    context = {
        'result': result,
        'quiz': quiz,
        'total_questions': total_questions,
        'accuracy': round(accuracy, 1),
        'is_robot_challenge': is_robot_challenge,
        'ai_score': ai_score,
        'answered_questions': answered_questions
    }
    return render(request, 'quiz/quiz_result.html', context)


@login_required
def export_quiz_result_pdf(request, quiz_id):
    """Export quiz result as PDF"""
    try:
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        result = QuizResult.objects.filter(user=request.user, quiz=quiz).latest('timestamp')
        total_questions = quiz.questions.count()
        
        # Check if this is from robot challenge
        is_robot_challenge = request.GET.get('challenge') == 'true'
        ai_score_str = request.GET.get('ai_score', None)
        ai_score = int(ai_score_str) if ai_score_str is not None else None
        
        # Only generate AI score if from robot challenge
        if is_robot_challenge and ai_score is None:
            ai_correct_answers = round(total_questions * 0.75)
            ai_score = ai_correct_answers + random.choice([-1, 0, 0, 1])
            ai_score = max(0, min(total_questions, ai_score))
        
        # Calculate accuracy percentage
        accuracy = (result.score / total_questions * 100) if total_questions > 0 else 0
        
        # Prepare user's answers
        answered_questions = []
        selected_map = result.selected_answers or {}
        for question in quiz.questions.all():
            qid = str(question.id)
            sel_id = selected_map.get(qid)
            selected_choice = None
            if sel_id is not None:
                try:
                    selected_choice = Choice.objects.get(pk=sel_id)
                except Choice.DoesNotExist:
                    selected_choice = None
            correct_choice = question.choices.filter(is_correct=True).first()
            answered_questions.append({
                'question': question,
                'selected': selected_choice,
                'correct': correct_choice,
                'is_correct': selected_choice.is_correct if selected_choice else False
            })
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Title
        if is_robot_challenge:
            title = Paragraph("🤖 Robot Challenge Results", title_style)
        else:
            title = Paragraph(f"{quiz.title} - Quiz Results", title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # User and Date Info
        user_info = f"<b>User:</b> {request.user.get_full_name() or request.user.username} | <b>Date:</b> {result.timestamp.strftime('%d %B %Y, %H:%M')}"
        story.append(Paragraph(user_info, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Score Section
        if is_robot_challenge and ai_score is not None:
            # Robot challenge comparison
            score_data = [
                ['Metric', 'Your Score', "AI Robot's Score"],
                ['Score', f"{result.score}/{total_questions}", f"{ai_score}/{total_questions}"],
                ['Accuracy', f"{accuracy:.1f}%", f"{(ai_score/total_questions*100):.1f}%"],
            ]
            if result.score > ai_score:
                winner = Paragraph("<b style='color: green;'>🎉 You Win! 🎉</b>", heading_style)
            elif result.score < ai_score:
                winner = Paragraph("<b style='color: orange;'>🤖 AI Wins! 🤖</b>", heading_style)
            else:
                winner = Paragraph("<b style='color: blue;'>🤝 It's a Tie! 🤝</b>", heading_style)
            story.append(winner)
        else:
            # Regular quiz
            score_data = [
                ['Score', f"{result.score}/{total_questions}"],
                ['Accuracy', f"{accuracy:.1f}%"],
            ]
        
        story.append(Spacer(1, 0.1*inch))
        
        # Score table
        score_table = Table(score_data, colWidths=[2*inch, 2*inch, 2*inch] if is_robot_challenge else [2*inch, 2*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9eef8')])
        ]))
        story.append(score_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Detailed Answers Section
        story.append(Paragraph("Detailed Answers", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        for idx, item in enumerate(answered_questions, 1):
            # Question
            q_text = Paragraph(f"<b>Q{idx}: {item['question'].text}</b>", normal_style)
            story.append(q_text)
            
            # Your Answer
            if item['selected']:
                status_text = "✓ Correct" if item['is_correct'] else "✗ Incorrect"
                your_answer = f"<b>Your Answer:</b> {item['selected'].text} ({status_text})"
            else:
                your_answer = "<b>Your Answer:</b> <i>No answer</i> (✗ Incorrect)"
            story.append(Paragraph(your_answer, normal_style))
            
            # Correct Answer
            if item['correct']:
                correct_answer = f"<b>Correct Answer:</b> {item['correct'].text}"
                story.append(Paragraph(correct_answer, normal_style))
                
                # Explanation
                if item['correct'].explanation:
                    explanation = f"<b>Explanation:</b> {item['correct'].explanation}"
                    story.append(Paragraph(explanation, normal_style))
            
            story.append(Spacer(1, 0.1*inch))
            
            # Page break every 3 questions to keep it readable
            if idx % 3 == 0 and idx < len(answered_questions):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create response
        filename = f"{quiz.title.replace(' ', '_')}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')
        return response
        
    except QuizResult.DoesNotExist:
        return JsonResponse({'error': 'Quiz result not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Specific quiz leaderboard
def leaderboard(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    results = QuizResult.objects.filter(quiz=quiz).order_by('-score', 'timestamp')
    return render(request, 'quiz/leaderboard.html', {'quiz': quiz, 'results': results})

# Page showing all leaderboards
def all_leaderboards(request):
    quizzes = Quiz.objects.all()
    return render(request, 'quiz/all_leaderboards.html', {'quizzes': quizzes})

# AI Robot Challenge page
def robot_challenge(request):
    quizzes = Quiz.objects.all()
    return render(request, 'quiz/robot_challenge.html', {'quizzes': quizzes})


# --- H2H Challenge Views ---

@login_required
def create_challenge(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    try:
        latest_result = QuizResult.objects.filter(user=request.user, quiz=quiz).latest('timestamp')
        challenger_score = latest_result.score
    except QuizResult.DoesNotExist:
        return redirect('quiz_detail', quiz_id=quiz_id)

    challenge = Challenge.objects.create(
        quiz=quiz,
        challenger=request.user,
        challenger_score=challenger_score
    )
    return redirect('challenge_lobby', challenge_id=challenge.id)


@login_required
def join_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    
    if request.user == challenge.challenger:
        return redirect('challenge_lobby', challenge_id=challenge.id)

    if challenge.status == 'completed':
        return redirect('challenge_result', challenge_id=challenge.id)

    context = {
        'challenge': challenge,
        'quiz': challenge.quiz
    }
    return render(request, 'quiz/join_challenge.html', context)


@login_required
def challenge_result(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    context = {
        'challenge': challenge,
        'quiz': challenge.quiz
    }
    return render(request, 'quiz/challenge_result.html', context)


@login_required
def challenge_lobby(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    
    if request.user != challenge.challenger:
        return HttpResponseForbidden("This is not your challenge.")
        
    challenge_url = request.build_absolute_uri(reverse('join_challenge', args=[challenge_id]))
    
    context = {
        'challenge': challenge,
        'challenge_url': challenge_url,
        'quiz': challenge.quiz
    }
    return render(request, 'quiz/challenge_lobby.html', context)

@login_required
def my_challenges(request):
    sent_challenges = Challenge.objects.filter(
        challenger=request.user, 
        status='waiting'
    ).order_by('-created_at')

    completed_matches = Challenge.objects.filter(
        Q(challenger=request.user) | Q(opponent=request.user),
        status='completed'
    ).order_by('-created_at')

    context = {
        'sent_challenges': sent_challenges,
        'completed_matches': completed_matches
    }
    return render(request, 'quiz/my_challenges.html', context)


# --- AUTO-MATCHMAKING VIEWS ---

@login_required
def find_match(request, quiz_id):
    """Find or create a match for auto-matchmaking - only pairs online users"""
    from datetime import timedelta
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    # Check if user already has a waiting match for this quiz
    existing_match = Matchmaking.objects.filter(
        Q(player1=request.user) | Q(player2=request.user),
        quiz=quiz,
        status__in=['waiting', 'in_progress']
    ).first()
    
    if existing_match:
        if existing_match.player2:
            return redirect('match_lobby', match_id=existing_match.id)
        return redirect('waiting_for_opponent', match_id=existing_match.id)
    
    # Only look for recent matches (less than 5 minutes old)
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    
    # Look for a waiting match where player1 is verified online
    waiting_matches = Matchmaking.objects.filter(
        quiz=quiz,
        player2__isnull=True,
        status='waiting',
        created_at__gte=five_minutes_ago
    ).exclude(player1=request.user).order_by('created_at')

    from .models import UserProfile
    # Debugging helpers: log match finding steps to Django logger
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"find_match called by user={request.user.username} for quiz={quiz.id}")
    print(f"[DEBUG] find_match called by user={request.user.username} for quiz={quiz.id}")
    for waiting_match in waiting_matches:
        logger.debug(f"considering waiting_match id={waiting_match.id} player1={waiting_match.player1.username} created_at={waiting_match.created_at}")
        print(f"[DEBUG] considering waiting_match id={waiting_match.id} player1={waiting_match.player1.username} created_at={waiting_match.created_at}")
        try:
            player1_profile = UserProfile.objects.get(user=waiting_match.player1)
        except UserProfile.DoesNotExist:
            # No profile found, delete stale match and continue
            logger.debug(f"deleting waiting_match id={waiting_match.id} because player1 profile missing")
            print(f"[DEBUG] deleting waiting_match id={waiting_match.id} because player1 profile missing")
            waiting_match.delete()
            continue

        # If player1 appears offline, remove stale match
        if (timezone.now() - player1_profile.last_activity) >= timedelta(minutes=5):
            logger.debug(f"deleting waiting_match id={waiting_match.id} because player1 appears offline (last_activity={player1_profile.last_activity})")
            print(f"[DEBUG] deleting waiting_match id={waiting_match.id} because player1 appears offline (last_activity={player1_profile.last_activity})")
            waiting_match.delete()
            continue

        # Attempt an atomic conditional update to claim player2
        updated = Matchmaking.objects.filter(pk=waiting_match.pk, player2__isnull=True).update(
            player2=request.user,
            status='in_progress'
        )

        if updated:
            logger.debug(f"user={request.user.username} successfully claimed match id={waiting_match.id}")
            print(f"[DEBUG] user={request.user.username} successfully claimed match id={waiting_match.id}")
            # Successfully claimed the match
            return redirect('match_lobby', match_id=waiting_match.id)

        logger.debug(f"user={request.user.username} failed to claim match id={waiting_match.id}; it was claimed concurrently")
        print(f"[DEBUG] user={request.user.username} failed to claim match id={waiting_match.id}; it was claimed concurrently")

        # If updated == 0 someone else claimed it concurrently; try next

    # No suitable waiting match found (or all were claimed/stale) - create new match
    new_match = Matchmaking.objects.create(
        quiz=quiz,
        player1=request.user,
        status='waiting'
    )
    logger.debug(f"created new waiting match id={new_match.id} for user={request.user.username}")
    print(f"[DEBUG] created new waiting match id={new_match.id} for user={request.user.username}")
    return redirect('waiting_for_opponent', match_id=new_match.id)


@login_required
def waiting_for_opponent(request, match_id):
    """Page showing waiting for opponent"""
    match = get_object_or_404(Matchmaking, id=match_id)
    
    # Check if user is part of this match
    if request.user not in [match.player1, match.player2]:
        return HttpResponseForbidden("You are not part of this match.")
    
    # Check if opponent has joined
    if match.player2 and match.status == 'in_progress':
        return redirect('match_lobby', match_id=match.id)
    
    context = {
        'match': match,
        'quiz': match.quiz
    }
    return render(request, 'quiz/waiting_for_opponent.html', context)


@login_required
def match_lobby(request, match_id):
    """Match lobby where both players can see the quiz and start"""
    match = get_object_or_404(Matchmaking, id=match_id)
    
    # Check if user is part of this match
    if request.user not in [match.player1, match.player2]:
        return HttpResponseForbidden("You are not part of this match.")
    
    context = {
        'match': match,
        'quiz': match.quiz,
        'is_player1': request.user == match.player1
    }
    return render(request, 'quiz/match_lobby.html', context)


@login_required
def match_quiz(request, match_id):
    """Quiz page for matchmaking"""
    match = get_object_or_404(Matchmaking, id=match_id)
    quiz = match.quiz
    
    # Check if user is part of this match
    if request.user not in [match.player1, match.player2]:
        return HttpResponseForbidden("You are not part of this match.")
    
    if request.method == 'POST':
        # Calculate score
        score = 0
        questions = quiz.questions.all()
        selected_answers = {}
        for question in questions:
            selected_choice_id = request.POST.get(f'question_{question.id}')
            selected_answers[str(question.id)] = int(selected_choice_id) if selected_choice_id else None
            if selected_choice_id:
                try:
                    selected_choice = get_object_or_404(Choice, pk=selected_choice_id)
                    if selected_choice.is_correct:
                        score += 1
                except (ValueError, Choice.DoesNotExist):
                    continue
        
        # Update match with player's score
        if request.user == match.player1:
            match.player1_score = score
        else:
            match.player2_score = score
        
        # Check if both players have completed
        if match.player1_score is not None and match.player2_score is not None:
            match.status = 'completed'
            match.completed_at = timezone.now()
        
        match.save()
        
        # Save quiz result for leaderboard including selected answers
        QuizResult.objects.create(user=request.user, quiz=quiz, score=score, selected_answers=selected_answers)
        
        return redirect('match_result', match_id=match.id)
    
    # GET request - show the quiz
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
    
    context = {
        'quiz': quiz,
        'questions_data': questions_data,
        'match': match
    }
    return render(request, 'quiz/match_quiz.html', context)


@login_required
def match_result(request, match_id):
    """Show match results"""
    match = get_object_or_404(Matchmaking, id=match_id)
    
    # Check if user is part of this match
    if request.user not in [match.player1, match.player2]:
        return HttpResponseForbidden("You are not part of this match.")
    
    # Check if both players have completed
    if match.player1_score is None or match.player2_score is None:
        # One player hasn't completed yet, show waiting screen
        context = {
            'match': match,
            'quiz': match.quiz,
            'waiting': True
        }
        return render(request, 'quiz/match_result.html', context)
    
    context = {
        'match': match,
        'quiz': match.quiz,
        'current_user': request.user,
        'is_player1': request.user == match.player1,
        'user_score': match.player1_score if request.user == match.player1 else match.player2_score,
        'opponent_score': match.player2_score if request.user == match.player1 else match.player1_score,
        'opponent_name': match.player2.username if request.user == match.player1 else match.player1.username
    }
    return render(request, 'quiz/match_result.html', context)


@login_required
def share_match_result(request, match_id):
    """Create a QuizResult for the current user from a Matchmaking result and share it to profile."""
    match = get_object_or_404(Matchmaking, id=match_id)

    # Ensure user is part of match
    if request.user not in [match.player1, match.player2]:
        return HttpResponseForbidden('You are not part of this match.')

    # Ensure match completed
    if match.player1_score is None or match.player2_score is None:
        return JsonResponse({'error': 'Match not completed yet.'}, status=400)

    # Determine user's score
    user_score = match.player1_score if request.user == match.player1 else match.player2_score

    # Create a QuizResult record so ShareableResult (which points to QuizResult) can reference it
    quiz = match.quiz
    # Avoid duplicate QuizResult by checking for an existing one with same quiz, user and score
    existing = QuizResult.objects.filter(user=request.user, quiz=quiz, score=user_score).order_by('-timestamp').first()
    if existing:
        qr = existing
    else:
        qr = QuizResult.objects.create(
            user=request.user,
            quiz=quiz,
            score=user_score,
            selected_answers=None
        )

    # Create ShareableResult if not exists for this QuizResult
    ShareableResult.objects.get_or_create(user=request.user, quiz_result=qr, defaults={'is_public': True})

    # Return JSON with redirect to profile
    return JsonResponse({'success': True, 'redirect': reverse('user_profile', args=[request.user.username])})


@login_required
def export_match_result_pdf(request, match_id):
    """Export a match result summary as PDF (both players score comparison)."""
    try:
        match = get_object_or_404(Matchmaking, id=match_id)

        # Ensure user is part of match
        if request.user not in [match.player1, match.player2]:
            return HttpResponseForbidden('You are not part of this match.')

        # Ensure match completed
        if match.player1_score is None or match.player2_score is None:
            return JsonResponse({'error': 'Match not completed yet.'}, status=400)

        # Prepare PDF content
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=22, alignment=TA_CENTER, textColor=colors.HexColor('#667eea'))
        heading_style = ParagraphStyle('H', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#764ba2'))
        normal_style = ParagraphStyle('N', parent=styles['Normal'], fontSize=10)

        # Title
        story.append(Paragraph('Match Result', title_style))
        story.append(Spacer(1, 0.15*inch))

        # Match Info
        user_name = request.user.get_full_name() or request.user.username
        opponent = match.player2 if request.user == match.player1 else match.player1
        opponent_name = opponent.get_full_name() or opponent.username
        completed_at = match.completed_at or match.created_at
        info = f"<b>User:</b> {user_name} &nbsp; &nbsp; <b>Opponent:</b> {opponent_name} &nbsp; &nbsp; <b>Date:</b> {completed_at.strftime('%d %B %Y, %H:%M') }"
        story.append(Paragraph(info, normal_style))
        story.append(Spacer(1, 0.1*inch))

        # Score table
        quiz = match.quiz
        your_score = match.player1_score if request.user == match.player1 else match.player2_score
        opp_score = match.player2_score if request.user == match.player1 else match.player1_score
        score_data = [
            ['Metric', 'You', 'Opponent'],
            ['Quiz', quiz.title if quiz else 'N/A', ''],
            ['Score', f"{your_score}/{quiz.questions.count()}", f"{opp_score}/{quiz.questions.count()}"],
        ]
        tbl = Table(score_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.2*inch))

        # Result message
        if your_score > opp_score:
            story.append(Paragraph('You Win! 🎉', heading_style))
        elif your_score < opp_score:
            story.append(Paragraph('You Lost 😔', heading_style))
        else:
            story.append(Paragraph("It's a Tie 🤝", heading_style))

        # Quiz meta
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Quiz:</b> {quiz.title}", normal_style))
        story.append(Paragraph(f"<b>Topic:</b> {quiz.topic}", normal_style))
        story.append(Paragraph(f"<b>Difficulty:</b> {quiz.difficulty}", normal_style))

        doc.build(story)
        buffer.seek(0)

        filename = f"Match_{match.id}_{completed_at.strftime('%Y%m%d_%H%M%S')}.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def quiz_stats(request):
    """Show quiz statistics - success rate % per quiz and difficulty distribution"""
    all_quizzes = Quiz.objects.all()
    
    quiz_stats_list = []
    difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    
    for quiz in all_quizzes:
        # Get all results for this quiz
        results = QuizResult.objects.filter(quiz=quiz)
        total_attempts = results.count()
        
        if total_attempts > 0:
            # Calculate total possible score (count of questions)
            max_score = quiz.questions.count()
            
            # Calculate success rate (attempts where score >= half of max)
            successful_attempts = results.filter(score__gte=max_score // 2).count()
            success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
        else:
            success_rate = 0
            max_score = quiz.questions.count()
        
        # Track difficulty distribution
        difficulty_counts[quiz.difficulty] = difficulty_counts.get(quiz.difficulty, 0) + 1
        
        quiz_stats_list.append({
            'quiz': quiz,
            'total_attempts': total_attempts,
            'success_rate': round(success_rate, 1),
            'max_score': max_score,
        })
    
    # Sort by success rate (descending)
    quiz_stats_list.sort(key=lambda x: x['success_rate'], reverse=True)
    
    context = {
        'quiz_stats_list': quiz_stats_list,
        'difficulty_counts': difficulty_counts,
        'total_quizzes': len(all_quizzes),
    }
    return render(request, 'quiz/quiz_stats.html', context)


# ===== ACHIEVEMENTS & BADGES =====

def check_and_award_badges(user):
    """Check user progress and award badges if criteria are met"""
    # Count total quiz attempts (wins = attempts with score >= 50%)
    results = QuizResult.objects.filter(user=user)
    
    if results.exists():
        max_score_per_quiz = {}
        for result in results:
            max = max_score_per_quiz.get(result.quiz_id, result.quiz.questions.count())
            max_score_per_quiz[result.quiz_id] = max
        
        wins = sum(1 for r in results if r.score >= max_score_per_quiz[r.quiz_id] / 2)
        
        # 10 Wins Badge
        if wins >= 10:
            badge, _ = Badge.objects.get_or_create(
                badge_type='10_wins',
                defaults={
                    'name': '10 Wins',
                    'description': 'Achieved 10 successful quiz attempts',
                    'icon': 'trophy-fill',
                    'color': 'warning'
                }
            )
            UserAchievement.objects.get_or_create(user=user, badge=badge)
        
        # 50 Wins Badge
        if wins >= 50:
            badge, _ = Badge.objects.get_or_create(
                badge_type='50_wins',
                defaults={
                    'name': '50 Wins',
                    'description': 'Achieved 50 successful quiz attempts',
                    'icon': 'star-fill',
                    'color': 'danger'
                }
            )
            UserAchievement.objects.get_or_create(user=user, badge=badge)
        
        # 100 Wins Badge
        if wins >= 100:
            badge, _ = Badge.objects.get_or_create(
                badge_type='100_wins',
                defaults={
                    'name': '100 Wins',
                    'description': 'Achieved 100 successful quiz attempts',
                    'icon': 'crown-fill',
                    'color': 'success'
                }
            )
            UserAchievement.objects.get_or_create(user=user, badge=badge)
        
        # Perfect Score Badge
        from django.db.models import Count as CountFunc
        perfect_score_count = 0
        for result in results:
            if result.score == result.quiz.questions.count():
                perfect_score_count += 1
        if perfect_score_count >= 1:
            badge, _ = Badge.objects.get_or_create(
                badge_type='perfect_score',
                defaults={
                    'name': 'Perfect Score',
                    'description': 'Achieved a perfect score on a quiz',
                    'icon': '100',
                    'color': 'primary'
                }
            )
            UserAchievement.objects.get_or_create(user=user, badge=badge)
        
        # All Difficulties Badge - attempted all 3 difficulty levels
        difficulties = results.values_list('quiz__difficulty', flat=True).distinct()
        if len(difficulties) >= 3:
            badge, _ = Badge.objects.get_or_create(
                badge_type='all_difficulties',
                defaults={
                    'name': 'Master of All',
                    'description': 'Attempted quizzes of all difficulty levels',
                    'icon': 'lightning-fill',
                    'color': 'info'
                }
            )
            UserAchievement.objects.get_or_create(user=user, badge=badge)


@login_required
def user_profile(request, username):
    """View user profile with badges, achievements, and shared results"""
    viewed_user = get_object_or_404(User, username=username)
    
    # Get user's quiz results
    results = QuizResult.objects.filter(user=viewed_user).order_by('-timestamp')
    
    # Get achievements/badges
    achievements = UserAchievement.objects.filter(user=viewed_user).order_by('-earned_at')
    
    # Get shared results
    shared_results = ShareableResult.objects.filter(user=viewed_user, is_public=True).order_by('-shared_at')
    
    # Get followers and following counts
    followers_count = UserFollow.objects.filter(following=viewed_user).count()
    following_count = UserFollow.objects.filter(follower=viewed_user).count()
    
    # Check if current user follows this user
    is_following = False
    if request.user.is_authenticated:
        is_following = UserFollow.objects.filter(follower=request.user, following=viewed_user).exists()
    
    # Calculate stats
    total_quizzes = results.count()
    avg_score = results.aggregate(avg=Avg('score'))['avg'] or 0
    
    context = {
        'viewed_user': viewed_user,
        'results': results[:10],  # Last 10 results
        'achievements': achievements,
        'shared_results': shared_results,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following,
        'total_quizzes': total_quizzes,
        'avg_score': round(avg_score, 2),
    }
    return render(request, 'quiz/user_profile.html', context)


@login_required
def toggle_follow(request, username):
    """Follow or unfollow a user"""
    target_user = get_object_or_404(User, username=username)
    
    if request.user == target_user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
    
    follow_obj, created = UserFollow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )
    
    if not created:
        follow_obj.delete()
        return JsonResponse({'status': 'unfollowed'})
    
    return JsonResponse({'status': 'followed'})


@login_required
def user_followers(request, username):
    """View followers of a user"""
    viewed_user = get_object_or_404(User, username=username)
    
    # Get all followers
    followers = UserFollow.objects.filter(following=viewed_user).select_related('follower')
    
    # Get user's following list for UI purposes
    following_ids = UserFollow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    
    context = {
        'viewed_user': viewed_user,
        'followers': followers,
        'page_title': f"{viewed_user.username}'s Followers",
        'is_own_profile': request.user == viewed_user,
        'following_ids': list(following_ids),
    }
    return render(request, 'quiz/followers_list.html', context)


@login_required
def user_following(request, username):
    """View users that a user is following"""
    viewed_user = get_object_or_404(User, username=username)
    
    # Get all users being followed
    following = UserFollow.objects.filter(follower=viewed_user).select_related('following')
    
    # Get current user's following list
    my_following_ids = UserFollow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    
    context = {
        'viewed_user': viewed_user,
        'following': following,
        'page_title': f"Users {viewed_user.username} is Following",
        'is_own_profile': request.user == viewed_user,
        'my_following_ids': list(my_following_ids),
    }
    return render(request, 'quiz/following_list.html', context)


def user_discovery(request):
    """Discover and explore user profiles"""
    # Get top users by quiz attempts and achievements
    top_users = User.objects.annotate(
        quiz_count=Count('quizresult', distinct=True),
        badge_count=Count('achievements', distinct=True)
    ).order_by('-quiz_count', '-badge_count').filter(quiz_count__gt=0)[:20]
    
    context = {
        'top_users': top_users,
    }
    return render(request, 'quiz/user_discovery.html', context)


# ===== TIME-BASED LEADERBOARDS =====

def leaderboard_weekly(request, quiz_id):
    """Weekly leaderboard for a specific quiz"""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    week_ago = timezone.now() - timedelta(days=7)
    
    results = QuizResult.objects.filter(
        quiz=quiz,
        timestamp__gte=week_ago
    ).values('user__username', 'user').annotate(
        top_score=Count('user')
    ).order_by('-top_score')
    
    # Get detailed scores
    leaderboard = []
    for result in results:
        user_results = QuizResult.objects.filter(
            quiz=quiz,
            user_id=result['user'],
            timestamp__gte=week_ago
        ).order_by('-score')
        
        if user_results.exists():
            leaderboard.append({
                'user': User.objects.get(id=result['user']),
                'attempts': user_results.count(),
                'best_score': user_results.first().score,
                'avg_score': round(user_results.aggregate(avg=Avg('score'))['avg'], 2)
            })
    
    context = {
        'quiz': quiz,
        'leaderboard': leaderboard,
        'period': 'Weekly'
    }
    return render(request, 'quiz/leaderboard_time.html', context)


def leaderboard_monthly(request, quiz_id):
    """Monthly leaderboard for a specific quiz"""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    month_ago = timezone.now() - timedelta(days=30)
    
    results = QuizResult.objects.filter(
        quiz=quiz,
        timestamp__gte=month_ago
    ).values('user__username', 'user').annotate(
        top_score=Count('user')
    ).order_by('-top_score')
    
    # Get detailed scores
    leaderboard = []
    for result in results:
        user_results = QuizResult.objects.filter(
            quiz=quiz,
            user_id=result['user'],
            timestamp__gte=month_ago
        ).order_by('-score')
        
        if user_results.exists():
            leaderboard.append({
                'user': User.objects.get(id=result['user']),
                'attempts': user_results.count(),
                'best_score': user_results.first().score,
                'avg_score': round(user_results.aggregate(avg=Avg('score'))['avg'], 2)
            })
    
    context = {
        'quiz': quiz,
        'leaderboard': leaderboard,
        'period': 'Monthly'
    }
    return render(request, 'quiz/leaderboard_time.html', context)


# ===== SHARE RESULTS =====

@login_required
def share_result(request, result_id):
    """Share a quiz result with custom message"""
    quiz_result = get_object_or_404(QuizResult, pk=result_id, user=request.user)
    
    if request.method == 'POST':
        message = request.POST.get('message', '')
        is_public = request.POST.get('is_public', 'on') == 'on'
        
        share, _ = ShareableResult.objects.get_or_create(
            user=request.user,
            quiz_result=quiz_result,
            defaults={'message': message, 'is_public': is_public}
        )
        
        return redirect('user_profile', username=request.user.username)
    
    context = {
        'quiz_result': quiz_result,
    }
    return render(request, 'quiz/share_result.html', context)


@login_required
def view_shared_result(request, share_id):
    """View a shared result"""
    shared_result = get_object_or_404(ShareableResult, pk=share_id, is_public=True)
    
    # Increment view count
    shared_result.views_count += 1
    shared_result.save(update_fields=['views_count'])
    
    quiz_result = shared_result.quiz_result
    quiz = quiz_result.quiz
    
    # Get answered questions
    answered_questions = []
    selected_map = quiz_result.selected_answers or {}
    for question in quiz.questions.all():
        qid = str(question.id)
        sel_id = selected_map.get(qid)
        selected_choice = None
        if sel_id is not None:
            try:
                selected_choice = Choice.objects.get(pk=sel_id)
            except Choice.DoesNotExist:
                selected_choice = None
        correct_choice = question.choices.filter(is_correct=True).first()
        answered_questions.append({
            'question': question,
            'selected': selected_choice,
            'correct': correct_choice,
            'is_correct': selected_choice.is_correct if selected_choice else False
        })
    
    context = {
        'shared_result': shared_result,
        'quiz_result': quiz_result,
        'quiz': quiz,
        'answered_questions': answered_questions,
        'total_questions': quiz.questions.count(),
    }
    return render(request, 'quiz/view_shared_result.html', context)


@login_required
def delete_shared_result(request, share_id):
    """Delete a shared result"""
    shared_result = get_object_or_404(ShareableResult, pk=share_id)
    
    # Check if the current user is the owner
    if shared_result.user != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    shared_result.delete()
    
    return JsonResponse({'success': True, 'message': 'Result deleted successfully'})


# ===== PROFILE EDITING =====

@login_required
def edit_profile(request):
    """Edit user profile - photo, bio, and basic info"""
    # Get or create UserProfile
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        user_form = UserBasicForm(request.POST, instance=request.user)
        
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            return redirect('user_profile', username=request.user.username)
    else:
        profile_form = UserProfileForm(instance=user_profile)
        user_form = UserBasicForm(instance=request.user)
    
    context = {
        'profile_form': profile_form,
        'user_form': user_form,
    }
    return render(request, 'quiz/edit_profile.html', context)


# ===== NOTIFICATIONS =====

@login_required
def notifications(request):
    """Display all notifications for the user"""
    user_notifications = Notification.objects.filter(user=request.user)
    unread_count = user_notifications.filter(is_read=False).count()
    
    context = {
        'notifications': user_notifications,
        'unread_count': unread_count,
    }
    return render(request, 'quiz/notifications.html', context)


@login_required
def mark_notification_as_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'is_read': True})
    
    return redirect('notifications')


@login_required
def mark_all_notifications_as_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications')


@login_required
def get_unread_notifications_count(request):
    """Get unread notification count (for AJAX)"""
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': unread_count})