import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import quiz.routing # Yeh file 'quiz/routing.py' ko import karta hai

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')

application = ProtocolTypeRouter({
    # Normal (HTTP) requests ke liye Django ka default istemaal karein
    "http": get_asgi_application(),
    
    # Live (WebSocket) connections ke liye Channels ka istemaal karein
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # Yahaan hum 'routes' argument pass kar rahe hain
            quiz.routing.websocket_urlpatterns
        )
    ),
})