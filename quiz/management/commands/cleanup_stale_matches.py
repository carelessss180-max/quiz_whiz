from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from quiz.models import UserProfile, Matchmaking

class Command(BaseCommand):
    help = 'Clean up stale matches from offline users'

    def handle(self, *args, **options):
        # Find matches where player1 is offline (no activity for 5+ minutes)
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        
        # Get offline users
        offline_users = UserProfile.objects.filter(
            last_activity__lt=five_minutes_ago
        ).values_list('user_id', flat=True)
        
        # Delete waiting matches from offline users
        deleted_count, _ = Matchmaking.objects.filter(
            player1_id__in=offline_users,
            player2__isnull=True,
            status='waiting'
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} stale matches from offline users')
        )
