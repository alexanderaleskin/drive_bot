from telegram_django_bot.permissions import BasePermissionClass

from .models import ShareLink


class CheckFolderPermissions(BasePermissionClass):
    def has_permissions(self, model, bot, update, user, utrl_args, **kwargs):
        share_link = ShareLink.objects.filter(
            folder=model,
            mountinstance__user_id=user.id
        ).first()

        if share_link.type_link == ShareLink.TYPE_SHOW_CHANGE:
            
            return True
        return False


class CheckFilePermissions(BasePermissionClass):
    def has_permissions(self, model, bot, update, user, utrl_args, **kwargs):
        share_link = ShareLink.objects.filter(
            file=model,
            mountinstance__user_id=user.id
        ).first()

        if share_link.type_link == ShareLink.TYPE_SHOW_CHANGE:
            
            return True
        return False
