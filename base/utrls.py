from django.urls import re_path

from .views import start, FileViewSet, FolderViewSet, ShareLinkViewSet
from telegram_django_bot.td_viewset import UserViewSet


urlpatterns = [
    re_path('start', start, name='start'),
    re_path('main_menu', start, name='start'),

    re_path('fl/', FileViewSet, name='FileViewSet'),
    re_path('fol/', FolderViewSet, name='FolderViewSet'),
    re_path('sl/', ShareLinkViewSet, name='ShareLinkViewSet'),
    re_path('us/', UserViewSet, name='UserViewSet')
]
