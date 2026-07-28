from .models import FriendRequest, Chat
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()


def are_friends(user1, user2):
    return (
        FriendRequest.objects.filter(
            Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1)
        )
        .filter(status=FriendRequest.StatusChoice.ACCEPTED)
        .exists()
    )


def get_friends(user):
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.ACCEPTED
    ).filter(Q(from_user=user) | Q(to_user=user))

    friends = []
    for fr in friend_requests:
        if user == fr.from_user:
            friends.append(fr.to_user)
        else:
            friends.append(fr.from_user)
    return friends


def get_or_create_chat(user1, user2):
    if user1.id > user2.id:
        user1, user2 = user2, user1
    chat, _ = Chat.objects.get_or_create(user1=user1, user2=user2)
    return chat


def has_user_send_snap_today(chat, user):
    return (
        chat.messages.filter(sender=user, created_at__date=timezone.now())
        .filter(image="")
        .filter(image=None)
        .exists()
    )


def is_continous_streak(last_streak_updated_at, now):
    return last_streak_updated_at.date() + timedelta(days=1) == now.date()


def update_streak(chat: Chat):
    now = timezone.now()
    if chat.streak_updated_at.date() == now.date():
        return

    user1_snap = has_user_send_snap_today(chat, chat.user1)
    user2_snap = has_user_send_snap_today(chat, chat.user2)

    if user1_snap and user2_snap:
        if is_continous_streak(chat.streak_updated_at, now):
            chat.streak += 1
        else:
            chat.streak = 1
        chat.streak_updated_at = now
        chat.save()
