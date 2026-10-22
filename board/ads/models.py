from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

from django.utils import timezone
from datetime import timedelta
from django.db.models import Q


class Category(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('URL', max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AdQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status='published', is_moderated=True).from_active_authors()

    def from_active_authors(self):
        now = timezone.now()
        return self.exclude(
            Q(author__ban__is_permanent=True) |
            Q(author__ban__expires_at__gt=now) 
        )


class Ad(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликовано'),
        ('archived', 'В архиве'),
    ]

    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('URL', max_length=220, unique=True, blank=True, allow_unicode=True)
    description = models.TextField('Описание')
    price = models.DecimalField('Цена', max_digits=12, decimal_places=2)
    image = models.ImageField('Изображение', upload_to='ads/%Y/%m/', blank=True, null=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ads', verbose_name='Категория'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='ads', verbose_name='Автор'
    )
    phone = models.CharField('Телефон', max_length=20)
    city = models.CharField('Город', max_length=100)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='published')
    is_moderated = models.BooleanField('Проверено модератором', default=False)
    views = models.PositiveIntegerField('Просмотры', default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    objects = AdQuerySet.as_manager()

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', 'is_moderated']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True)[:200] or 'ad'
            slug, i = base, 1
            while Ad.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('ads:ad_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title



class UserBan(models.Model):
    REASON_CHOICES = [
        ('spam', 'Спам и реклама'),
        ('fraud', 'Мошенничество'),
        ('abuse', 'Оскорбления и агрессия'),
        ('rules', 'Нарушение правил'),
        ('other', 'Другое'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='ban', verbose_name='Пользователь'
    )
    reason = models.CharField('Причина', max_length=20, choices=REASON_CHOICES, default='rules')
    comment = models.TextField('Комментарий модератора', blank=True)
    banned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bans_issued', verbose_name='Забанил'
    )
    banned_at = models.DateTimeField('Дата бана', auto_now_add=True)
    expires_at = models.DateTimeField('Бан до', null=True, blank=True)
    is_permanent = models.BooleanField('Навсегда', default=False)

    class Meta:
        verbose_name = 'Бан пользователя'
        verbose_name_plural = 'Баны пользователей'
        ordering = ['-banned_at']

    def __str__(self):
        return f'Бан: {self.user.username}'

    @property
    def is_active(self):
        if self.is_permanent:
            return True
        if self.expires_at is None:
            return True
        return self.expires_at > timezone.now()

    def time_left(self):
        if self.is_permanent or not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return delta if delta.total_seconds() > 0 else None

    def save(self, *args, **kwargs):
        if self.is_permanent:
            self.expires_at = None
        super().save(*args, **kwargs)
        # Автоматически снимаем с публикации все объявления
        if self.is_active:
            Ad.objects.filter(author=self.user).update(
                status='archived', is_moderated=False
            )


class Favorite(models.Model):
    """Объявление в избранном у пользователя."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites'
    )
    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'ad')
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class Message(models.Model):
    """Личное сообщение между пользователями (по объявлению)."""
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages'
    )
    ad = models.ForeignKey(
        Ad, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages'
    )
    text = models.TextField('Текст')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']