"""URL's for the chat app."""

from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('chats/', views.ChatSessionView.as_view()),
    path('chats/history/', views.ChatHistoryView.as_view()),
    path('chats/<uri>/', views.ChatSessionView.as_view()),
    path('chats/<uri>/messages/', views.ChatSessionMessageView.as_view()),
    path('friends/request/', views.send_friend_request),
    path('friends/requests/', views.list_friend_requests),
    path('friends/respond/', views.respond_friend_request),
    path('friends/', views.list_friends),

]
