from django.utils.translation import gettext_lazy as _
from telegram_django_bot import forms as td_forms

from .models import File, Folder, ShareLink

class FileForm(td_forms.TelegaModelForm):
    form_name = _("Menu file")

    class Meta:
        model = File
        fields = ['media_id', 'name','message_format', 'text', 'folder', 'user']


class FolderForm(td_forms.TelegaModelForm):
    form_name = _("Menu folder")

    class Meta:
        model = Folder
        fields = ['name', 'user', 'parent']


class ShareLinkForm(td_forms.TelegaModelForm):
    form_name = _('Menu sharelink')

    class Meta:
        model = ShareLink
        fields = ['file', 'folder', 'type_link', 'share_amount','share_code']
