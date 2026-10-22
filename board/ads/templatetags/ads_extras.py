from django import template
from ads.models import Favorite

register = template.Library()


@register.simple_tag
def is_favorited(user, ad):
    """True, если объявление в избранном у пользователя."""
    if not user.is_authenticated:
        return False
    return Favorite.objects.filter(user=user, ad=ad).exists()


@register.simple_tag
def favorites_count(user):
    """Сколько объявлений в избранном у пользователя."""
    if not user.is_authenticated:
        return 0
    return Favorite.objects.filter(user=user).count()