from django.shortcuts import render

# Create your views here.

from django.contrib.auth import get_user_model
from .models import (
    ChatSession, ChatSessionMember, ChatSessionMessage, deserialize_user
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from notifications.utils import notify
from notifications import default_settings as notifs_settings
import json

class ChatSessionView(APIView):
    """Manage Chat sessions."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """create a new chat session."""
        user = request.user

        chat_session = ChatSession.objects.create(owner=user)

        return Response({
            'status': 'SUCCESS', 'uri': chat_session.uri,
            'message': 'New chat session created'
        })

    def patch(self, request, *args, **kwargs):
        """Add a user to a chat session."""
        User = get_user_model()

        uri = kwargs['uri']
        username = request.data['username']
        user = User.objects.get(username=username)

        chat_session = ChatSession.objects.get(uri=uri)
        owner = chat_session.owner

        if owner != user:  # Only allow non owners join the room             chat_session.members.get_or_create(
                user=user, chat_session=chat_session

        owner = deserialize_user(owner)
        members = [
            deserialize_user(chat_session.user) 
            for chat_session in chat_session.members.all()
        ]
        members.insert(0, owner)  # Make the owner the first member 
        return Response ({
            'status': 'SUCCESS', 'members': members,
            'message': '%s joined the chat' % user.username,
            'user': deserialize_user(user)
        })
    

class ChatSessionMessageView(APIView):
    """Create/Get Chat session messages."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """return all messages in a chat session."""
        uri = kwargs['uri']

        chat_session = ChatSession.objects.get(uri=uri)
        messages = [chat_session_message.to_json() 
            for chat_session_message in chat_session.messages.all()]

        return Response({
            'id': chat_session.id, 'uri': chat_session.uri,
            'messages': messages
        })

    def post(self, request, *args, **kwargs):
        uri = kwargs['uri']
        message = request.data['message']

        user = request.user
        chat_session = ChatSession.objects.get(uri=uri)

        chat_session_message = ChatSessionMessage.objects.create(
            user=user, chat_session=chat_session, message=message
        )

        # Get channel layer and send to group
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"chat_{chat_session.uri}",  # group name matches consumer
            {
                "type": "chat_message",  # calls chat_message() in consumer
                "message": chat_session_message.to_json(),
                "user": deserialize_user(user)
            }
        )
        print("📩 Sent message to WebSocket group:", chat_session.uri)
        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'message': message,
            'user': deserialize_user(user)
        })
