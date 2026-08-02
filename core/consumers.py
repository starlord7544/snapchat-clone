import base64
import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Chat, Message
from django.db.models import Q
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404


def _decode_base64_image(data_url):
	header, _, encoded = data_url.partition(",")
	ext = "png"
	if "image/" in header:
		ext = header.split("image/")[1].split(";")[0] or "png"
	return ContentFile(base64.b64decode(encoded), name=f"{uuid.uuid4().hex}.{ext}")


class ChatConsumer(AsyncWebsocketConsumer):
	async def connect(self):
		user = self.scope["user"]

		if not user.is_authenticated:
			await self.close()
			return 

		self.chat_id = self.scope["url_route"]["kwargs"].get("chat_id")
		self.group_name = f"chat_{self.chat_id}"
  
		allowed = await self._is_chat_member(user.id, self.chat_id)
		if not allowed:
			await self.close()
			return

		await self.channel_layer.group_add(self.group_name, self.channel_name)

		await self.accept()
  
	async def disconnect(self, code):
		if hasattr(self, "group_name"):
			await self.channel_layer.group_discard(self.group_name, self.channel_name)

	async def receive(self, text_data = None):
		user = self.scope["user"]
		payload = json.loads(text_data)
		text = payload.get("message", "")
		image = payload.get("image")

		if not text and not image:
			return

		saved = await self._save_message(self.chat_id, user.id, text, image)
		await self.channel_layer.group_send(self.group_name, {
			"type": "chat_message",
			"text": saved["text"],
			"image_url": saved["image_url"],
			"sender_id": saved["sender_id"],
			"sender_username": saved["sender_username"],
			"created_at": saved["created_at"]
		})
		return

	async def chat_message(self, event):
		await self.send(
      		text_data=json.dumps({
				"text": event["text"],
				"image_url": event.get("image_url"),
				"sender_id": event["sender_id"],
				"sender_username": event["sender_username"],
				"created_at": event["created_at"]
			})
        )
  
  
	@database_sync_to_async
	def _is_chat_member(self, user_id, chat_id):
		return (
      		Chat.objects.filter(id=chat_id)
        	.filter(Q(user1_id = user_id) | Q(user2_id = user_id))
         	.exists()
      	)
	
 
	@database_sync_to_async
	def _save_message(self, chat_id, sender_id, text_message, image_data=None):
		sender = get_object_or_404(get_user_model(), pk=sender_id)
		chat = Chat.objects.get(pk=chat_id)

		receiver = chat.user1 if sender.id == chat.user1.id else chat.user2

		image_file = _decode_base64_image(image_data) if image_data else None
		message = Message.objects.create(
			chat_id=chat_id, sender=sender, reciever=receiver, text=text_message, image=image_file
		)
		now = timezone.now()
		chat.last_message = now
		chat.save()

		return {
			"text": message.text,
			"image_url": message.image.url if message.image else None,
			"sender_id": sender_id,
			"sender_username": sender.get_username(),
			"created_at": now.isoformat(),
		}
