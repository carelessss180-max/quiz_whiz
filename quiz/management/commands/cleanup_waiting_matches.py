from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from quiz.models import Matchmaking

class Command(BaseCommand):
    help = 'Clean up stale waiting matches older than 5 minutes'

    def handle(self, *args, **options):
        five_min_ago = timezone.now() - timedelta(minutes=5)
        
        # Delete waiting matches older than 5 minutes
        old_waiting = Matchmaking.objects.filter(
            status='waiting',
            created_at__lt=five_min_ago
        )
        count = old_waiting.count()
        old_waiting.delete()
        
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} stale waiting matches'))
        
        # Show current state
        waiting_count = Matchmaking.objects.filter(status='waiting').count()
        in_prog_count = Matchmaking.objects.filter(status='in_progress').count()
        completed_count = Matchmaking.objects.filter(status='completed').count()
        
        self.stdout.write(f'Waiting: {waiting_count} | In-Progress: {in_prog_count} | Completed: {completed_count}')
