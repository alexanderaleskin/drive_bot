from django.urls import re_path

from .views import start, change_location, select_folder, FileViewSet, FolderViewSet, ShareLinkViewSet
from telegram_django_bot.user_viewset import UserViewSet


urlpatterns = [
    re_path('start', start, name='start'),
    re_path('main_menu', start, name='start'),

    re_path('change_location', change_location, name='change_location'),
    re_path('select_folder', select_folder, name='select_folder'),

    re_path('fl/', FileViewSet, name='FileViewSet'),
    re_path('fol/', FolderViewSet, name='FolderViewSet'),
    re_path('sl/', ShareLinkViewSet, name='ShareLinkViewSet'),
    re_path('us/', UserViewSet, name='UserViewSet')
]
