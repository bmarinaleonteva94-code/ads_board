from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    # --- Служебные страницы ---
    path('register/', views.register_view, name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('banned/', views.banned_view, name='banned'),

    # --- Личный кабинет ---
    path('my/', views.my_ads, name='my_ads'),
    path('favorites/', views.favorites, name='favorites'),
    path('messages/', views.messages_view, name='messages'),

    # --- Модерация ---
    path('moderation/ban/<int:user_id>/', views.ban_user, name='ban_user'),
    path('moderation/unban/<int:user_id>/', views.unban_user, name='unban_user'),

    # --- Объявления  ---
    path('', views.ad_list, name='ad_list'),
    path('ad/create/', views.ad_create, name='ad_create'),
    path('ad/<str:slug>/edit/', views.ad_edit, name='ad_edit'),
    path('ad/<str:slug>/delete/', views.ad_delete, name='ad_delete'),
    path('ad/<str:slug>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('ad/<str:slug>/', views.ad_detail, name='ad_detail'),  
]