from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Quiz, Notification


@receiver(post_save, sender=Quiz)
def notify_users_on_new_quiz(sender, instance, created, **kwargs):
    """
    Signal handler: Notify ALL users when a new quiz is created (including admin)
    """
    if created:
        # Get all users (including admin/staff)
        all_users = User.objects.all()
        
        # Create notifications for each user
        notifications = [
            Notification(
                user=user,
                notification_type='new_quiz',
                title=f'New Quiz: {instance.title}',
                message=f'A new {instance.difficulty} quiz "{instance.title}" on {instance.topic} has been added! Start playing now.',
                quiz=instance
            )
            for user in all_users
        ]
        
        # Bulk create all notifications
        Notification.objects.bulk_create(notifications)
