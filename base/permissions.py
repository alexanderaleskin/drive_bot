from telegram_django_bot.permissions import BasePermissionClass
from .models import ShareLink, Folder, File


class CheckFolderPermission(BasePermissionClass):
    def help_check_func(self, CheckClass, field_name, user, utrl_args):
        method = utrl_args[0]

        instance = None

        if method != 'cr':
            instance_id = utrl_args[1]
            instance = CheckClass.objects.get(id=instance_id)
        elif utrl_args[1] == field_name:
            instance_id = utrl_args[2]
            instance = Folder.objects.get(id=instance_id)

        if instance:
            if user.id != instance.user_id:
                if method in ['se', 'sl']:
                    check_types =[ShareLink.TYPE_SHOW_WITH_COPY, ShareLink.TYPE_SHOW_CHANGE]
                else:
                    check_types = [ShareLink.TYPE_SHOW_CHANGE]

                return True, check_types, instance
        return False, None, None



    def has_permissions(self, bot, update, user, utrl_args, **kwargs):
        need_extra_check, check_types, folder = self.help_check_func(Folder, 'parent', user, utrl_args)

        if need_extra_check:
                return ShareLink.objects.filter(
                    type_link__in=check_types,
                    mountinstance__user_id=user.id,
                    folder_id__in=folder.get_ancestors(include_self=True)
                ).count()
        return True


class CheckFilePermission(CheckFolderPermission):
    def has_permissions(self, bot, update, user, utrl_args, **kwargs):
        need_extra_check, check_types, file_or_folder = self.help_check_func(File, 'folder', user, utrl_args)

        if need_extra_check:
            sharelink_queryset = ShareLink.objects.filter(
                type_link__in=check_types,
                mountinstance__user_id=user.id,
            )
            folder = getattr(file_or_folder, 'folder', file_or_folder)
            if sharelink_queryset.filter(folder_id__in=folder.get_ancestors(include_self=True)).count() == 0:
                if hasattr(file_or_folder, 'folder'): # then it is file
                    return sharelink_queryset.filter(file_id=file_or_folder.id).count()
                else:
                    return False
        return True
