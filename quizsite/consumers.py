# quiz/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChallengeConsumer(AsyncWebsocketConsumer):
    # Yeh lists har quiz lobby ke liye waiting users ko store karengi
    # Note: Yeh ek basic implementation hai. Asli production app mein, hum ise Redis ya database mein store karte.
    waiting_pools = {}

    async def connect(self):
        self.user = self.scope["user"]
        self.quiz_id = self.scope['url_route']['kwargs']['quiz_id']
        self.room_group_name = f'challenge_{self.quiz_id}'

        # Check karein agar user logged in hai
        if not self.user.is_authenticated:
            await self.close()
            return

        await self.accept()

        # Is quiz ke liye waiting pool banayein agar nahi hai toh
        if self.quiz_id not in self.waiting_pools:
            self.waiting_pools[self.quiz_id] = []

        # Check karein ki kya pehle se koi wait kar raha hai
        if len(self.waiting_pools[self.quiz_id]) > 0:
            # Match mil gaya!
            opponent_channel = self.waiting_pools[self.quiz_id].pop(0)
            
            # Ek unique match ID banayein (dono ke channel names se)
            match_id = f"match_{opponent_channel.channel_name}_{self.channel_name}"
            
            # Dono users ko batao ki match shuru ho gaya hai
            # Opponent ko message bhejein
            await self.channel_layer.send(
                opponent_channel.channel_name,
                {
                    "type": "game_start",
                    "match_id": match_id,
                    "opponent": self.user.username,
                }
            )
            # Khud ko message bhejein
            await self.send(text_data=json.dumps({
                'type': 'game_start',
                'match_id': match_id,
                'opponent': (await self.get_user_by_channel(opponent_channel.channel_name)).username
            }))
            
        else:
            # Koi nahi hai, waiting pool mein add ho jayein
            self.waiting_pools[self.quiz_id].append(self)
            await self.send(text_data=json.dumps({
                'type': 'waiting_for_opponent'
            }))
    
    async def disconnect(self, close_code):
        # Agar user disconnect hota hai, to use waiting pool se hata dein
        if self.quiz_id in self.waiting_pools and self in self.waiting_pools[self.quiz_id]:
            self.waiting_pools[self.quiz_id].remove(self)

    # Yeh function doosre user ko game start message bhejta hai
    async def game_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_start',
            'match_id': event['match_id'],
            'opponent': event['opponent']
        }))
        
    # Helper function (ise baad mein implement karna hoga)
    async def get_user_by_channel(self, channel_name):
        # Is function ko database se user fetch karne ke liye update karna hoga
        # Abhi ke liye hum placeholder use kar rahe hain
        return self.user # Yeh aage update hoga

    # Jab browser se koi message aaye (jaise "answer")
    async def receive(self, text_data):
        # Is logic ko hum "Step 3" mein implement karenge
        pass