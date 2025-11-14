# quiz/routing.py
from django.urls import re_path
from . import consumers

# Yeh URLconf sirf WebSockets ke liye hai
websocket_urlpatterns = [
    # Hum har quiz ke liye ek alag live "lobby" banayenge
    re_path(r'ws/challenge/(?P<quiz_id>\d+)/$', consumers.ChallengeConsumer.as_asgi()),
]