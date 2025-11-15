import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from .models import Quiz, Question, QuizResult, Choice, Challenge, Matchmaking, Badge, UserAchievement, UserFollow, ShareableResult, UserProfile, Notification
from .forms import UserProfileForm, UserBasicForm
from django.db.models import Q, Count, Avg, F
from django.http import HttpResponseForbidden, JsonResponse, FileResponse
from django.utils import timezone
from django.db import transaction
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
        from .forms import SignupForm
        form = SignupForm(request.POST)
        print(f"[SIGNUP] Form submitted. Is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"[SIGNUP] Form errors: {form.errors}")
            # Still render with errors shown
            return render(request, 'quiz/signup.html', {'form': form})
        
        email = form.cleaned_data['email']
        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']
        print(f"[SIGNUP] Processing signup for email: {email}, username: {username}")
        
        # Create OTP and send email
        from .models import EmailOTP
        from django.core.mail import send_mail
        
        otp_obj = EmailOTP.create_otp(email)
        print(f"[SIGNUP] OTP created: {otp_obj.otp}")
        
        # Try to send OTP email
        try:
            from django.core.mail import EmailMultiAlternatives
            
            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h2 style="color: #333; margin-bottom: 20px;">Welcome to QuizWhiz! 🎉</h2>
                        
                        <p style="color: #666; font-size: 16px; line-height: 1.6;">
                            We're excited to have you join our community. To complete your signup, please use the OTP below:
                        </p>
                        
                        <div style="background-color: #f0f0f0; border-left: 4px solid #007bff; padding: 20px; margin: 25px 0; border-radius: 4px;">
                            <p style="margin: 0; color: #666; font-size: 14px; margin-bottom: 10px;">Your One-Time Password (OTP):</p>
                            <p style="margin: 0; font-size: 32px; font-weight: bold; color: #007bff; letter-spacing: 3px; font-family: 'Courier New', monospace;">
                                {otp_obj.otp}
                            </p>
                        </div>
                        
                        <p style="color: #999; font-size: 13px; margin: 20px 0;">
                            ⏰ This OTP is valid for <strong>10 minutes</strong>. If you didn't request this, please ignore this email.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                            QuizWhiz - Test Your Knowledge<br>
                            © 2024 All rights reserved
                        </p>
                    </div>
                </body>
            </html>
            """
            
            subject = 'QuizWhiz - Email Verification OTP'
            text_message = f'Your OTP for QuizWhiz signup is: {otp_obj.otp}\n\nThis OTP is valid for 10 minutes.'
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email='noreply@quizwhiz.com',
                to=[email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
            
            print(f"[EMAIL] OTP sent to {email}: {otp_obj.otp}")
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send OTP to {email}: {e}")
        
        # Store signup data in session and redirect to OTP verification
        request.session['signup_username'] = username
        request.session['signup_email'] = email
        request.session['signup_password'] = password
        print(f"[SIGNUP] Session data stored, redirecting to verify_otp")
        
        return redirect('verify_otp')
    else:
        from .forms import SignupForm
        form = SignupForm()
    return render(request, 'quiz/signup.html', {'form': form})


def verify_otp(request):
    """Verify OTP and create user account"""
    email = request.session.get('signup_email')
    username = request.session.get('signup_username')
    password = request.session.get('signup_password')
    
    if not email or not username:
        return redirect('signup')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()
        
        from .models import EmailOTP
        try:
            otp_obj = EmailOTP.objects.get(email=email)
            is_valid, message = otp_obj.verify_otp(otp_code)
            
            if is_valid:
                # Create user account
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                # Create user profile
                from .models import UserProfile
                UserProfile.objects.create(user=user)
                
                # Clear session data
                del request.session['signup_username']
                del request.session['signup_email']
                del request.session['signup_password']
                
                # Log user in
                login(request, user)
                return redirect('home')
            else:
                return render(request, 'quiz/verify_otp.html', {
                    'email': email,
                    'error': message
                })
        except EmailOTP.DoesNotExist:
            return render(request, 'quiz/verify_otp.html', {
                'email': email,
                'error': 'OTP not found. Please sign up again.'
            })
    
    return render(request, 'quiz/verify_otp.html', {'email': email})


def resend_otp(request):
    """Resend OTP to user email"""
    email = request.session.get('signup_email')
    
    if not email:
        return redirect('signup')
    
    from .models import EmailOTP
    from django.core.mail import send_mail
    
    otp_obj = EmailOTP.create_otp(email)
    
    try:
        from django.core.mail import EmailMultiAlternatives
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Your New OTP 🔐</h2>
                    
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        Here's your new One-Time Password (OTP) for QuizWhiz signup verification:
                    </p>
                    
                    <div style="background-color: #f0f0f0; border-left: 4px solid #28a745; padding: 20px; margin: 25px 0; border-radius: 4px;">
                        <p style="margin: 0; color: #666; font-size: 14px; margin-bottom: 10px;">Your New OTP:</p>
                        <p style="margin: 0; font-size: 32px; font-weight: bold; color: #28a745; letter-spacing: 3px; font-family: 'Courier New', monospace;">
                            {otp_obj.otp}
                        </p>
                    </div>
                    
                    <p style="color: #999; font-size: 13px; margin: 20px 0;">
                        ⏰ This OTP is valid for <strong>10 minutes</strong>.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                        QuizWhiz - Test Your Knowledge<br>
                        © 2024 All rights reserved
                    </p>
                </div>
            </body>
        </html>
        """
        
        subject = 'QuizWhiz - Email Verification OTP (Resent)'
        text_message = f'Your new OTP for QuizWhiz signup is: {otp_obj.otp}\n\nThis OTP is valid for 10 minutes.'
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email='noreply@quizwhiz.com',
            to=[email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        
        print(f"[EMAIL] OTP resent to {email}: {otp_obj.otp}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to resend OTP to {email}: {e}")
    
    return redirect('verify_otp')


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

# --- PASSWORD RESET VIEWS ---
def forgot_password(request):
    """Request password reset link"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(email=email)
            from .models import PasswordReset
            from django.core.mail import EmailMultiAlternatives
            
            reset_obj = PasswordReset.create_reset(user)
            
            # Send reset email
            reset_link = request.build_absolute_uri(f'/reset-password/{reset_obj.token}/')
            
            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h2 style="color: #333;">Reset Your Password 🔐</h2>
                        <p style="color: #666; font-size: 16px;">Hi {user.first_name or user.username},</p>
                        
                        <p style="color: #666;">We received a request to reset your password. Click the button below to set a new password:</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_link}" style="display: inline-block; background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
                        </div>
                        
                        <p style="color: #999; font-size: 13px;">This link is valid for 24 hours. If you didn't request this, please ignore this email.</p>
                        
                        <p style="color: #999; font-size: 13px;">Or copy this link: <code style="background-color: #f0f0f0; padding: 2px 5px; border-radius: 3px;">{reset_link}</code></p>
                        
                        <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                        <p style="color: #999; font-size: 12px; text-align: center;">QuizWhiz © 2024</p>
                    </div>
                </body>
            </html>
            """
            
            msg = EmailMultiAlternatives(
                subject='QuizWhiz - Password Reset Request',
                body=f'Click this link to reset your password: {reset_link}',
                from_email='noreply@quizwhiz.com',
                to=[user.email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
            
            print(f"[EMAIL] Password reset link sent to {user.email}")
            
            return render(request, 'quiz/forgot_password.html', {
                'success': True,
                'message': 'Password reset link sent to your email!'
            })
        except User.DoesNotExist:
            return render(request, 'quiz/forgot_password.html', {
                'success': True,
                'message': 'If this email exists, you will receive a password reset link.'
            })
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send password reset: {e}")
            return render(request, 'quiz/forgot_password.html', {
                'error': 'Failed to send reset link. Please try again.'
            })
    
    return render(request, 'quiz/forgot_password.html')


def reset_password(request, token):
    """Reset password using token"""
    from .models import PasswordReset
    
    try:
        reset_obj = PasswordReset.objects.get(token=token)
        
        if not reset_obj.is_valid():
            return render(request, 'quiz/reset_password.html', {
                'error': 'This reset link has expired or has been used.'
            })
        
        if request.method == 'POST':
            password1 = request.POST.get('password1', '').strip()
            password2 = request.POST.get('password2', '').strip()
            
            if not password1 or not password2:
                return render(request, 'quiz/reset_password.html', {
                    'error': 'Please enter a password.'
                })
            
            if password1 != password2:
                return render(request, 'quiz/reset_password.html', {
                    'error': 'Passwords do not match.'
                })
            
            if len(password1) < 8:
                return render(request, 'quiz/reset_password.html', {
                    'error': 'Password must be at least 8 characters long.'
                })
            
            # Update password
            user = reset_obj.user
            user.set_password(password1)
            user.save()
            
            # Mark token as used
            reset_obj.is_used = True
            reset_obj.save()
            
            print(f"[AUTH] Password reset for {user.username}")
            
            return render(request, 'quiz/reset_password.html', {
                'success': True,
                'message': 'Password reset successfully! You can now login with your new password.'
            })
        
        return render(request, 'quiz/reset_password.html', {'token': token})
    
    except PasswordReset.DoesNotExist:
        return render(request, 'quiz/reset_password.html', {
            'error': 'Invalid reset link.'
        })

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
    
    # Send email notification
    from .models import EmailNotification
    try:
        # Only send quiz result emails when enabled in settings
        if getattr(settings, 'SEND_RESULT_EMAILS', False):
            EmailNotification.create_quiz_result_email(request.user, result)
    except Exception as e:
        print(f"[EMAIL] Failed to send quiz result email: {e}")
    
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
    
    # Use transaction with select_for_update for safe, serialized access
    with transaction.atomic():
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        
        # Lock all waiting matches for this quiz
        waiting_matches = Matchmaking.objects.select_for_update().filter(
            quiz=quiz,
            player2__isnull=True,
            status='waiting',
            created_at__gte=five_minutes_ago
        ).exclude(player1=request.user).order_by('created_at')

        from .models import UserProfile
        for waiting_match in waiting_matches:
            try:
                player1_profile = UserProfile.objects.get(user=waiting_match.player1)
            except UserProfile.DoesNotExist:
                waiting_match.delete()
                continue

            if (timezone.now() - player1_profile.last_activity) >= timedelta(minutes=5):
                waiting_match.delete()
                continue

            # Claim the match (within transaction, so safe)
            waiting_match.player2 = request.user
            waiting_match.status = 'in_progress'
            waiting_match.save()
            
            print(f"[DEBUG] user={request.user.username} successfully claimed match id={waiting_match.id}")
            return redirect('match_lobby', match_id=waiting_match.id)

        # No suitable waiting match - create new one
        new_match = Matchmaking.objects.create(
            quiz=quiz,
            player1=request.user,
            status='waiting'
        )
        print(f"[DEBUG] created new waiting match id={new_match.id} for user={request.user.username}")
        return redirect('waiting_for_opponent', match_id=new_match.id)



@login_required
def waiting_for_opponent(request, match_id):
    """Page showing waiting for opponent"""
    match = get_object_or_404(Matchmaking, id=match_id)
    
    # Check if user is part of this match
    if request.user not in [match.player1, match.player2]:
        return HttpResponseForbidden("You are not part of this match.")
    
    # If match progressed, send user to lobby
    if match.player2 and match.status == 'in_progress':
        return redirect('match_lobby', match_id=match.id)
    
    context = {
        'match': match,
        'quiz': match.quiz
    }
    return render(request, 'quiz/waiting_for_opponent.html', context)


@login_required
def api_find_match(request, quiz_id):
    """JSON endpoint to find or create a match for auto-matchmaking (used by AJAX).
    
    Strategy: Lock the entire quiz's matchmaking records, check for waiting matches,
    and either claim one or create new one. Use get_or_create with careful logic.
    """
    import time
    req_id = str(time.time())[-6:]
    print(f"\n[{req_id}] api_find_match START: user={request.user.username}, quiz_id={quiz_id}")
    
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    # If user already in a match, return that
    existing_match = Matchmaking.objects.filter(
        Q(player1=request.user) | Q(player2=request.user),
        quiz=quiz,
        status__in=['waiting', 'in_progress']
    ).first()
    if existing_match:
        if existing_match.player2:
            print(f"[{req_id}] → User already matched in {existing_match.id}")
            return JsonResponse({'status': 'matched', 'match_id': str(existing_match.id), 'match_lobby_url': reverse('match_lobby', args=[existing_match.id])})
        print(f"[{req_id}] → User already waiting in {existing_match.id}")
        return JsonResponse({'status': 'waiting', 'match_id': str(existing_match.id)})

    print(f"[{req_id}] → Starting atomic matching transaction...")
    
    # Use atomic transaction to ensure consistency
    with transaction.atomic():
        five_minutes_ago = timezone.now() - timedelta(minutes=5)

        # Lock ALL Matchmaking records for this quiz to serialize access
        # This ensures only one request processes at a time for this quiz
        locked_matches = list(Matchmaking.objects.select_for_update().filter(
            quiz=quiz,
            created_at__gte=five_minutes_ago
        ))
        print(f"[{req_id}] → Acquired lock on {len(locked_matches)} total matches for quiz")

        # Now find waiting matches that can be claimed
        waiting_matches = Matchmaking.objects.filter(
            quiz=quiz,
            player2__isnull=True,
            status='waiting',
            created_at__gte=five_minutes_ago
        ).exclude(player1=request.user).order_by('created_at')

        waiting_count = waiting_matches.count()
        print(f"[{req_id}] → Found {waiting_count} waiting matches to consider")

        from .models import UserProfile
        for waiting_match in waiting_matches:
            print(f"[{req_id}]   → Checking {waiting_match.id} (player1={waiting_match.player1.username})")
            try:
                player1_profile = UserProfile.objects.get(user=waiting_match.player1)
            except UserProfile.DoesNotExist:
                print(f"[{req_id}]   → Delete: no profile")
                waiting_match.delete()
                continue

            if (timezone.now() - player1_profile.last_activity) >= timedelta(minutes=5):
                print(f"[{req_id}]   → Delete: offline (last_activity={player1_profile.last_activity})")
                waiting_match.delete()
                continue

            # Try to claim this match
            print(f"[{req_id}]   → Attempting to claim {waiting_match.id}...")
            waiting_match.player2 = request.user
            waiting_match.status = 'in_progress'
            waiting_match.save()
            
            print(f"[{req_id}] ✓ SUCCESS: Matched! Claimed {waiting_match.id}")
            return JsonResponse({'status': 'matched', 'match_id': str(waiting_match.id), 'match_lobby_url': reverse('match_lobby', args=[waiting_match.id])})

        # No claimable waiting match found - create new one within the transaction
        print(f"[{req_id}]   → No suitable waiting match, creating new...")
        new_match = Matchmaking.objects.create(quiz=quiz, player1=request.user, status='waiting')
        print(f"[{req_id}] ✓ SUCCESS: Created waiting match {new_match.id}")
        return JsonResponse({'status': 'waiting', 'match_id': str(new_match.id)})





@login_required
def api_check_match(request, match_id):
    """JSON endpoint to check if a waiting match has been claimed."""
    match = get_object_or_404(Matchmaking, id=match_id)
    if match.player2 and match.status == 'in_progress':
        return JsonResponse({'status': 'matched', 'match_id': str(match.id), 'match_lobby_url': reverse('match_lobby', args=[match.id])})
    return JsonResponse({'status': 'waiting', 'match_id': str(match.id)})


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
    
    # Send email notification to both players
    from .models import EmailNotification
    try:
        # Only send match result emails when enabled in settings
        if getattr(settings, 'SEND_RESULT_EMAILS', False):
            if match.player1.email:
                EmailNotification.create_match_result_email(match.player1, match)
            if match.player2 and match.player2.email:
                EmailNotification.create_match_result_email(match.player2, match)
    except Exception as e:
        print(f"[EMAIL] Failed to send match result email: {e}")
    
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