from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import json, timezone
from django.contrib.auth import get_user_model
from .models import Chat, Message
from django.db.models import Q
from .utils import get_or_create_chat
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404

class ChatConsumer(AsyncWebsocketConsumer):
	async def connect(self):
		user = self.scope["user"]

		print(self.scope)
  
		if not user.is_authenticated:
			await self.close()
			return 

		self.chat_id = self.scope["url_route"]["kwargs"].get("chat_id")
		self.group_name = f"chat_{self.chat_id}"
  
		allowed = await self._is_chat_member(user.id, self.chat_id)
		if not allowed:
			await self.close()
			return

		self.channel_layer.group_add(self.group_name, self.channel_name)

		self.accept()
  
	async def disconnect(self, code):
		return self.channel_layer.group_discard(self.group_name, self.channel_name)
	
 
	async def receive(self, text_data = None):
		user = self.scope["user"]
		payload = json.loads(text_data)
		text = payload.get("message", "")

		if not text:
			return
  
		saved = await self._save_message(self.chat_id, user.id, text)
		self.channel_layer.group_send(self.group_name, {
			"type": "message",
			"message": saved["text"],
			"sender_id": saved["sender_id"],
			"sender_username": saved["sender_username"],
			"created_at": saved["created_at"]
		})
		return
  
  
	@database_sync_to_async
	async def _is_chat_member(self, user_id, chat_id):
		return (
      		Chat.objects.filter(id=chat_id)
        	.filter(Q(user1 = user_id) | Q(user2 = user_id))
         	.exists()
      	)
	
 
	@database_sync_to_async
	async def _save_message(self, chat_id, sender_id, text_message):
		sender = get_object_or_404(get_user_model(), pk=sender_id)
		chat = Chat.objects.get(pk=chat_id)
  
		receiver = chat.user1 if sender.id == chat.user1.id else chat.user2
  
		message = Message.objects.create(chat_id=chat_id, sender=sender, receiver=receiver, text=text_message)
		now = timezone.now()
		chat.last_message = now
		chat.save()
  
		return {
			"text": message.text,
			"sender_id": sender_id,
			"sender_username": sender.get_username(),
			"created_at": now,
		}
