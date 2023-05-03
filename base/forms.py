from django.utils.translation import gettext_lazy as _
from django import forms
from telegram_django_bot import forms as td_forms

from .models import File, Folder, ShareLink, MountInstance


class FileForm(td_forms.TelegramModelForm):
    form_name = _("Menu file")

    class Meta:
        model = File
        fields = ['media_id', 'name', 'message_format', 'text', 'folder', 'user']

        labels = {
            'text': _('Note'),
            'name': _('Name'),
        }

        widgets = {
            'name': forms.HiddenInput(),
        }


class FolderForm(td_forms.TelegramModelForm):
    form_name = _("Menu folder")

    class Meta:
        model = Folder
        fields = ['name', 'user', 'parent']

        labels = {
            'name': _('Folder name'),
        }


class ShareLinkForm(td_forms.TelegramModelForm):
    form_name = _('Menu sharelink')

    class Meta:
        model = ShareLink
        fields = ['folder', 'file', 'type_link', 'share_amount','share_code']

        widgets = {
            'folder': forms.HiddenInput(),
            'file': forms.HiddenInput(),
            'share_code': forms.HiddenInput(),
        }

        labels = {
            'type_link': _('How to share'),
            'share_amount': _('Share with amount'),
        }


    def clean(self):
        cleaned_data = super().clean()

        if (folder:= cleaned_data.get('folder')):
            if folder.parent_id is None:
                self.add_error('folder', _('Main folder could not be shared'))

            mounts_in_family = MountInstance.objects.filter(
                mount_folder_id__in=folder.get_descendants(include_self=False).values_list('id', flat=True),
                user=self.user
            ).count()

            shared_folders = ShareLink.objects.filter(
                folder_id__in=folder.get_family().values_list('id', flat=True),
                # folder__user=self.user,
            ).exclude(folder_id=folder.id).count()

            if mounts_in_family or shared_folders:
                self.add_error('folder', _(
                    'There is mounted or shared folders instances in descendants. You could not share this folder. \n'
                ))

        return cleaned_data



