from telegram_django_bot.permissions import BasePermissionClass


class CheckFolderPermission(BasePermissionClass):
    def has_permissions(self, bot, update, user, utrl_args, **kwargs):

        return
