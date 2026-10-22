from django.contrib import admin
from django.utils.html import format_html
from .models import Ad, Category, UserBan
from django.utils import timezone
from datetime import timedelta


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'ads_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    @admin.display(description='Объявлений')
    def ads_count(self, obj):
        return obj.ads.count()


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = (
        'thumbnail', 'title', 'author', 'category',
        'price', 'city', 'status', 'is_moderated', 'views', 'created_at'
    )
    list_display_links = ('title',)
    list_filter = ('status', 'is_moderated', 'category', 'created_at')
    list_editable = ('status', 'is_moderated')
    search_fields = ('title', 'description', 'city', 'phone', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('views', 'created_at', 'updated_at', 'image_preview')
    date_hierarchy = 'created_at'
    list_per_page = 25
    autocomplete_fields = ('author',)

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'slug', 'description', 'price', 'category')
        }),
        ('Изображение', {
            'fields': ('image', 'image_preview')
        }),
        ('Контакты', {
            'fields': ('phone', 'city')
        }),
        ('Публикация', {
            'fields': ('author', 'status', 'is_moderated', 'views')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['approve_ads', 'archive_ads', 'unpublish_ads']

    @admin.display(description='Фото')
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:45px;border-radius:4px;object-fit:cover;">',
                obj.image.url
            )
        return '—'

    @admin.display(description='Превью')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:250px;border-radius:6px;">', obj.image.url)
        return 'Нет изображения'

    @admin.action(description='✅ Одобрить и опубликовать')
    def approve_ads(self, request, queryset):
        n = queryset.update(is_moderated=True, status='published')
        self.message_user(request, f'Одобрено: {n}')

    @admin.action(description='📦 Переместить в архив')
    def archive_ads(self, request, queryset):
        n = queryset.update(status='archived')
        self.message_user(request, f'В архив: {n}')

    @admin.action(description='🚫 Снять с публикации')
    def unpublish_ads(self, request, queryset):
        n = queryset.update(status='draft', is_moderated=False)
        self.message_user(request, f'Снято с публикации: {n}')


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'reason', 'is_permanent', 'expires_at',
        'banned_by', 'banned_at', 'status_badge'
    )
    list_filter = ('reason', 'is_permanent', 'banned_at')
    search_fields = ('user__username', 'user__email', 'comment')
    readonly_fields = ('banned_at',)
    autocomplete_fields = ('user', 'banned_by')
    date_hierarchy = 'banned_at'

    fieldsets = (
        ('Кого баним', {'fields': ('user', 'reason', 'comment')}),
        ('Срок', {'fields': ('is_permanent', 'expires_at')}),
        ('Кто забанил', {'fields': ('banned_by', 'banned_at')}),
    )

    actions = ['ban_7_days', 'ban_30_days', 'ban_forever', 'unban']

    @admin.display(description='Статус')
    def status_badge(self, obj):
        if obj.is_active:
            if obj.is_permanent:
                return format_html('<span style="color:#c0392b;font-weight:700;">🔴 Навсегда</span>')
            return format_html(
                '<span style="color:#e67e22;font-weight:600;">🟠 до {}</span>',
                obj.expires_at.strftime('%d.%m.%Y %H:%M')
            )
        return format_html('<span style="color:#27ae60;">🟢 истёк</span>')

    @admin.action(description='Забанить на 7 дней')
    def ban_7_days(self, request, queryset):
        self._apply_ban(request, queryset, days=7)

    @admin.action(description='Забанить на 30 дней')
    def ban_30_days(self, request, queryset):
        self._apply_ban(request, queryset, days=30)

    @admin.action(description='Забанить навсегда')
    def ban_forever(self, request, queryset):
        self._apply_ban(request, queryset, days=None)

    @admin.action(description='Разбанить')
    def unban(self, request, queryset):
        n = queryset.delete()[0]
        self.message_user(request, f'Разбанено: {n}')

    def _apply_ban(self, request, queryset, days):
        expires = timezone.now() + timedelta(days=days) if days else None
        for ban in queryset:
            ban.banned_by = request.user
            ban.is_permanent = days is None
            ban.expires_at = expires
            ban.save()
        self.message_user(request, f'Обновлено: {queryset.count()}')