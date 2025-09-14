import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.uri = self.scope['url_route']['kwargs']['uri']
        self.room_group_name = f"chat_{self.uri}"
        print("🔗 WebSocket connected to room:", self.room_group_name)
        # Join the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group
        print("❌ WebSocket disconnected from room:", self.room_group_name)
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def chat_message(self, event):
        # Send the event's message back to the WebSocket
        print(f"🔥 WebSocket got event: {event}  ")

        await self.send(text_data=json.dumps({
            "message": event["message"]["message"],  # extract just the text
            "user": event["user"]
        }))
