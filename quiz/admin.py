from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Quiz, Question, Choice, QuizResult, Challenge, UserProfile, Matchmaking, Notification

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3 

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'time_limit')

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'difficulty', 'is_featured', 'created_at')
    list_filter = ('difficulty', 'is_featured', 'created_at')
    search_fields = ('title', 'topic')
    fields = ('title', 'topic', 'difficulty', 'is_featured', 'created_at')
    readonly_fields = ('created_at',)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_activity', 'is_online')
    readonly_fields = ('last_activity',)
    fields = ('user', 'last_activity')

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'created_at', 'is_read', 'send_to_all_link')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at', 'send_all_users_button')
    fields = ('send_all_users_button', 'user', 'notification_type', 'title', 'message', 'quiz', 'is_read', 'created_at')
    
    def send_to_all_link(self, obj):
        """Show a link to send this notification to all users"""
        return format_html(
            '<a class="button" href="?send_to_all={}">Send to All</a>',
            obj.pk,
        )
    send_to_all_link.short_description = 'Actions'
    
    def send_all_users_button(self, obj=None):
        """Display button for sending notification to all users (only on add page)"""
        if not obj:  # Only on add page
            return format_html(
                '<div style="background: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px;">'
                '<strong>💡 Tip:</strong> After creating the notification, you can send it to all users '
                'by clicking the "Send to All" link in the list view.'
                '</div>'
            )
        return ""
    send_all_users_button.short_description = 'Send to All Users'
    
    def get_readonly_fields(self, request, obj=None):
        """Make created_at readonly only when editing"""
        if obj:  # Editing existing notification
            return self.readonly_fields
        return ['created_at', 'send_all_users_button']
    
    def changelist_view(self, request, extra_context=None):
        """Handle sending notification to all users"""
        send_to_all = request.GET.get('send_to_all')
        if send_to_all:
            try:
                notification = Notification.objects.get(pk=send_to_all)
                all_users = User.objects.exclude(id=notification.user.id)
                
                notifications_to_create = [
                    Notification(
                        user=user,
                        notification_type=notification.notification_type,
                        title=notification.title,
                        message=notification.message,
                        quiz=notification.quiz
                    )
                    for user in all_users
                ]
                
                Notification.objects.bulk_create(notifications_to_create)
                
                self.message_user(
                    request,
                    f'✅ Notification sent to {len(all_users)} users successfully!',
                    level='success'
                )
            except Notification.DoesNotExist:
                self.message_user(request, 'Notification not found.', level='error')
        
        return super().changelist_view(request, extra_context)

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(QuizResult)
admin.site.register(Challenge)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Matchmaking)
admin.site.register(Notification, NotificationAdmin)