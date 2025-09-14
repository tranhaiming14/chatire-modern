from urllib import request
from django.db.models import Q
# Create your views here.

from django.contrib.auth import get_user_model
from .models import (
    ChatSession, ChatSessionMember, ChatSessionMessage, deserialize_user, User, FriendRequest, Friendship
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import JsonResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from notifications.utils import notify
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404

from notifications import default_settings as notifs_settings
import json

class ChatSessionView(APIView):
    """Manage Chat sessions."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """create a new chat session."""
        user = request.user

        chat_session = ChatSession.objects.create(owner=user)
        ChatSessionMember.objects.create(
            chat_session=chat_session,
            user=user
        )

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

        if owner != user and not chat_session.members.filter(user=user).exists():  # Only allow non owners join the room
            ChatSessionMember.objects.create(
                chat_session=chat_session,
                user=user
            )

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
class ChatHistoryView(APIView):
    def get(self, request, *args, **kwargs):
        print("DEBUG user:", request.user)  # <- Add this

        """Return chat history for the logged-in user."""
        user = request.user
        sessions = ChatSession.objects.filter(
            Q(owner=user) | Q(members__user=user)
        ).distinct()
        data = [{'uri': s.uri, 'name': f"Chat with {', '.join(m.user.username for m in s.members.exclude(user=user))}"} for s in sessions]
        return JsonResponse(data, safe=False)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_friend_request(request):
    username = request.data.get('username')
    if username == request.user.username:
        return Response({'error': 'You cannot add yourself'}, status=400)

    to_user = get_object_or_404(User, username=username)

    fr, created = FriendRequest.objects.get_or_create(
        from_user=request.user,
        to_user=to_user
    )
    if not created:
        return Response({'error': 'Request already sent'}, status=400)
    print(f"Friend request sent from {request.user.username} to {to_user.username}")
    return Response({'status': 'SUCCESS', 'message': f'Friend request sent to {to_user.username}'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_friend_requests(request):
    requests = FriendRequest.objects.filter(to_user=request.user, status='pending')
    data = [{'id': r.id, 'from_user': r.from_user.username, 'created_at': r.created_at} for r in requests]
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def respond_friend_request(request):
    fr_id = request.data.get('id')
    action = request.data.get('action')  # 'accept' or 'decline'
    fr = get_object_or_404(FriendRequest, id=fr_id, to_user=request.user)

    if action == 'accept':
        fr.status = 'accepted'
        fr.save()

        # Store friendship (avoid duplicates)
        Friendship.objects.get_or_create(
            user1=min(request.user, fr.from_user, key=lambda u: u.id),
            user2=max(request.user, fr.from_user, key=lambda u: u.id)
        )

        # Create a private chat session
        chat_session = ChatSession.objects.create(owner=request.user)
        ChatSessionMember.objects.create(chat_session=chat_session, user=request.user)
        ChatSessionMember.objects.create(chat_session=chat_session, user=fr.from_user)

        return Response({'status': 'accepted', 'chat_uri': chat_session.uri})

    elif action == 'decline':
        fr.status = 'declined'
        fr.save()
        return Response({'status': 'declined'})

    return Response({'error': 'Invalid action'}, status=400)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_friends(request):
    friendships = Friendship.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    friends = []
    for f in friendships:
        if f.user1 == request.user:
            friends.append(f.user2.username)
        else:
            friends.append(f.user1.username)
    return Response(friends)
