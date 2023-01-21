from django.urls import re_path

from .views import start, FileViewSet, FolderViewSet


urlpatterns = [
        re_path('start', start, name='start'),
        re_path('main_menu', start, name='start'),

        re_path('fl/', FileViewSet, name='FileViewSet'),
        re_path('fol/', FolderViewSet, name='FolderViewSet'),
    ]
