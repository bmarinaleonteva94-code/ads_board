from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class BanCheckMiddleware(MiddlewareMixin):
    """Разлогинивает забаненных и редиректит на /banned/."""

    EXEMPT_URLS = ('/admin/', '/logout/', '/banned/', '/static/', '/media/')

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        if any(request.path.startswith(u) for u in self.EXEMPT_URLS):
            return None

        ban = getattr(request.user, 'ban', None)

        if ban and ban.is_active:
            request.session['banned_user_id'] = request.user.pk
            logout(request)
            return redirect('ads:banned')

        if ban and not ban.is_active:
            ban.delete()

        return None