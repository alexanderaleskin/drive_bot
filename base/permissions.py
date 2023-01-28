from telegram_django_bot.permissions import BasePermissionClass

from .models import ShareLink


class CheckFolderPermissions(BasePermissionClass):
    def has_permissions(self, bot, update, user, utrl_args, **kwargs):
        if kwargs:
            share_link = ShareLink.objects.filter(
                folder_id=kwargs['model'].pk,
                mountinstance__user=user
            ).first()

            if share_link.type_link == ShareLink.TYPE_SHOW_CHANGE:
            
                return True
            return False
        return True


class CheckFilePermissions(BasePermissionClass):
    def has_permissions(self, bot, update, user, utrl_args=None, **kwargs):
        if kwargs:
            share_link = ShareLink.objects.filter(
                file_id=kwargs['model'].pk,
                mountinstance__user=user
            ).first()

            if share_link.type_link == ShareLink.TYPE_SHOW_CHANGE:
            
                return True
            return False
        return True
