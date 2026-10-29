from django.db.models import Count
from .models import Favorite, Message


def counters(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'favorites_count': Favorite.objects.filter(user=request.user).count(),
        'unread_messages_count': Message.objects.filter(
            recipient=request.user, is_read=False
        ).count(),
    }