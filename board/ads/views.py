from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AdForm, RegisterForm, MessageForm
from .models import Ad, Category, Favorite, Message, User, UserBan

# ============================================================
#  СПИСОК ОБЪЯВЛЕНИЙ
# ============================================================
def ad_list(request):
    """Лента опубликованных объявлений с поиском, фильтрами и пагинацией."""
    ads = Ad.objects.published().select_related('category', 'author')

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    city = request.GET.get('city', '').strip()
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort', 'new')

    if q:
        ads = ads.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if cat:
        ads = ads.filter(category__slug=cat)
    if city:
        ads = ads.filter(city__icontains=city)
    if min_price:
        ads = ads.filter(price__gte=min_price)
    if max_price:
        ads = ads.filter(price__lte=max_price)

    sorts = {
        'new': '-created_at',
        'old': 'created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'popular': '-views',
    }
    ads = ads.order_by(sorts.get(sort, '-created_at'))

    paginator = Paginator(ads, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    qs = request.GET.copy()
    qs.pop('page', None)

    return render(request, 'ads/ad_list.html', {
        'page_obj': page_obj,
        'categories': Category.objects.all(),
        'query': q,
        'category_slug': cat,
        'city': city,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'sort': sort,
        'querystring': qs.urlencode(),
    })


# ============================================================
#  ДЕТАЛЬНАЯ СТРАНИЦА ОБЪЯВЛЕНИЯ
# ============================================================
def ad_detail(request, slug):
    """Страница объявления. Увеличивает счётчик просмотров."""
    ad = get_object_or_404(
        Ad.objects.select_related('category', 'author'), slug=slug
    )

    allowed = (
        (ad.status == 'published' and ad.is_moderated)
        or request.user == ad.author
        or request.user.is_staff
    )
    if not allowed:
        messages.error(request, 'Объявление недоступно')
        return redirect('ads:ad_list')

    Ad.objects.filter(pk=ad.pk).update(views=F('views') + 1)
    ad.refresh_from_db()

    similar = (
        Ad.objects.published()
        .filter(category=ad.category)
        .exclude(pk=ad.pk)[:4]
        if ad.category else Ad.objects.none()
    )

    return render(request, 'ads/ad_detail.html', {
        'ad': ad,
        'similar': similar,
    })


# ============================================================
#  СОЗДАНИЕ / РЕДАКТИРОВАНИЕ / УДАЛЕНИЕ ОБЪЯВЛЕНИЯ
# ============================================================
@login_required
def ad_create(request):
    """Создание объявления. Отправляет его на модерацию."""
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.author = request.user
            ad.status = 'published'
            ad.is_moderated = False  
            ad.save()
            messages.success(request, 'Объявление отправлено на модерацию')
            return redirect('ads:my_ads')
    else:
        form = AdForm()

    return render(request, 'ads/ad_form.html', {
        'form': form,
        'title': 'Новое объявление',
    })


@login_required
def ad_edit(request, slug):
    """Редактирование объявления. После правок — снова на модерацию."""
    ad = get_object_or_404(Ad, slug=slug, author=request.user)

    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.is_moderated = False  
            ad.save()
            messages.success(request, 'Объявление обновлено и отправлено на модерацию')
            return redirect('ads:my_ads')
    else:
        form = AdForm(instance=ad)

    return render(request, 'ads/ad_form.html', {
        'form': form,
        'title': 'Редактировать',
    })


@login_required
def ad_delete(request, slug):
    """Удаление объявления с подтверждением."""
    ad = get_object_or_404(Ad, slug=slug, author=request.user)

    if request.method == 'POST':
        ad.delete()
        messages.success(request, 'Объявление удалено')
        return redirect('ads:my_ads')

    return render(request, 'ads/ad_confirm_delete.html', {'ad': ad})


# ============================================================
#  ЛИЧНЫЙ КАБИНЕТ
# ============================================================
@login_required
def my_ads(request):
    """Все объявления текущего пользователя."""
    ads = (
        Ad.objects
        .filter(author=request.user)
        .select_related('category')
        .order_by('-created_at')
    )
    return render(request, 'ads/my_ads.html', {'ads': ads})


# ============================================================
#  РЕГИСТРАЦИЯ / ВХОД / ВЫХОД
# ============================================================
def register_view(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect('ads:ad_list')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Добро пожаловать!')
            return redirect('ads:ad_list')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


class LoginView(DjangoLoginView):
    """Страница входа (наследник стандартной LoginView Django)."""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


def logout_view(request):
    """Выход пользователя."""
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('ads:ad_list')


# ============================================================
#  БЛОКИРОВКА ПОЛЬЗОВАТЕЛЕЙ
# ============================================================
def banned_view(request):
    """Страница 'вы забанены'. Показывает причину и срок."""
    user_id = request.session.pop('banned_user_id', None)
    ban = UserBan.objects.filter(user_id=user_id).first() if user_id else None
    return render(request, 'ads/banned.html', {'ban': ban})


@staff_member_required
def ban_user(request, user_id):
    """Забанить пользователя навсегда."""
    target = get_object_or_404(User, pk=user_id)

    if target.is_staff or target == request.user:
        messages.error(request, 'Нельзя забанить этого пользователя')
        return redirect('ads:ad_list')

    UserBan.objects.update_or_create(
        user=target,
        defaults={
            'reason': request.POST.get('reason', 'rules'),
            'comment': request.POST.get('comment', ''),
            'banned_by': request.user,
            'expires_at': None,
            'is_permanent': True,
        }
    )
    messages.success(request, f'Пользователь {target.username} забанен')
    return redirect('ads:ad_list')


@staff_member_required
def unban_user(request, user_id):
    """Снять бан."""
    UserBan.objects.filter(user_id=user_id).delete()
    messages.success(request, 'Бан снят')
    return redirect('ads:ad_list')


# ============================================================
#  ИЗБРАННОЕ
# ============================================================
@login_required
def favorites(request):
    """Список избранных объявлений пользователя."""
    items = (
        Favorite.objects
        .filter(user=request.user)
        .select_related('ad', 'ad__category')
        .order_by('-created_at')
    )
    return render(request, 'ads/favorites.html', {'items': items})


@require_POST
@login_required
def favorite_toggle(request, slug):
    """Добавить/убрать объявление из избранного (AJAX + fallback)."""
    ad = get_object_or_404(Ad, slug=slug)
    fav, created = Favorite.objects.get_or_create(user=request.user, ad=ad)

    if not created:
        fav.delete()
        is_fav = False
    else:
        is_fav = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'is_favorited': is_fav,
            'favorites_count': Favorite.objects.filter(user=request.user).count(),
        })

    messages.success(
        request,
        'Добавлено в избранное' if is_fav else 'Удалено из избранного'
    )
    return redirect(request.META.get('HTTP_REFERER', ad.get_absolute_url()))


# ============================================================
#  СООБЩЕНИЯ
# ============================================================
@login_required
def messages_view(request):
    """Список всех сообщений пользователя (входящие и исходящие)."""
    qs = (
        Message.objects
        .filter(Q(sender=request.user) | Q(recipient=request.user))
        .select_related('sender', 'recipient', 'ad')
        .order_by('-created_at')
    )

    Message.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    return render(request, 'ads/messages.html', {'messages_list': qs})



@login_required
def message_send(request, slug, user_id):
    """Отправка сообщения автору объявления."""
    ad = get_object_or_404(Ad, slug=slug)
    recipient = get_object_or_404(User, pk=user_id)

    if recipient == request.user:
        messages.error(request, 'Нельзя отправить сообщение самому себе')
        return redirect(ad.get_absolute_url())

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.recipient = recipient
            msg.ad = ad
            msg.save()
            messages.success(request, 'Сообщение отправлено')
            return redirect(ad.get_absolute_url())

    messages.error(request, 'Не удалось отправить сообщение')
    return redirect(ad.get_absolute_url())