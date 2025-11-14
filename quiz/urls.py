from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('latest/', views.latest_quizzes, name='latest_quizzes'),
    path('stats/', views.quiz_stats, name='quiz_stats'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('leaderboards/', views.all_leaderboards, name='all_leaderboards'),
    path('leaderboard/<int:quiz_id>/', views.leaderboard, name='leaderboard'),
    path('leaderboard/<int:quiz_id>/weekly/', views.leaderboard_weekly, name='leaderboard_weekly'),
    path('leaderboard/<int:quiz_id>/monthly/', views.leaderboard_monthly, name='leaderboard_monthly'),
    path('robot-challenge/', views.robot_challenge, name='robot_challenge'),
    
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:quiz_id>/result/', views.quiz_result, name='quiz_result'),
    path('quiz/<int:quiz_id>/result/export-pdf/', views.export_quiz_result_pdf, name='export_quiz_result_pdf'),

    # H2H Challenge URLs
    path('challenge/create/<int:quiz_id>/', views.create_challenge, name='create_challenge'),
    path('challenge/lobby/<uuid:challenge_id>/', views.challenge_lobby, name='challenge_lobby'),
    path('challenge/join/<uuid:challenge_id>/', views.join_challenge, name='join_challenge'),
    path('challenge/result/<uuid:challenge_id>/', views.challenge_result, name='challenge_result'),
    path('my-challenges/', views.my_challenges, name='my_challenges'),
    
    # Auto-Matchmaking URLs
    path('find-match/<int:quiz_id>/', views.find_match, name='find_match'),
    path('waiting/<uuid:match_id>/', views.waiting_for_opponent, name='waiting_for_opponent'),
    path('match/<uuid:match_id>/lobby/', views.match_lobby, name='match_lobby'),
    path('match/<uuid:match_id>/quiz/', views.match_quiz, name='match_quiz'),
    path('match/<uuid:match_id>/result/', views.match_result, name='match_result'),
    path('match/<uuid:match_id>/share/', views.share_match_result, name='share_match_result'),
    path('match/<uuid:match_id>/result/export-pdf/', views.export_match_result_pdf, name='export_match_result_pdf'),
    
    # User Profile & Social Features
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('profile/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),
    path('profile/<str:username>/followers/', views.user_followers, name='user_followers'),
    path('profile/<str:username>/following/', views.user_following, name='user_following'),
    path('discover/', views.user_discovery, name='user_discovery'),
    
    # Share Results
    path('result/<int:result_id>/share/', views.share_result, name='share_result'),
    path('shared/<int:share_id>/', views.view_shared_result, name='view_shared_result'),
    path('shared/<int:share_id>/delete/', views.delete_shared_result, name='delete_shared_result'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    path('notifications/unread-count/', views.get_unread_notifications_count, name='get_unread_notifications_count'),
]