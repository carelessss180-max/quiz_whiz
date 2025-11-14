from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import UserProfile

class UserActivityMiddleware(MiddlewareMixin):
    """
    Middleware to track user activity and update last_activity timestamp
    This marks users as online when they make any request
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Get or create UserProfile for the user
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            # Update last_activity to current time (auto_now=True does this automatically)
            profile.save()
        return None
