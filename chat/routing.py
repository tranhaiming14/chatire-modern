from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ws://host:port/ws/chat/<uri>/
    re_path(r'^/?ws/chat/(?P<uri>[^/]+)/?$', consumers.ChatConsumer.as_asgi()),
]
