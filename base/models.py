from telegram_django_bot.models import TelegramUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey
from telegram_django_bot.models import MESSAGE_FORMAT


class User(TelegramUser):
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Folder.objects.get_or_create(
            user=self,
            parent=None,
            defaults={'name': ''}
        )


class Folder(MPTTModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='folders',
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(
        max_length=256,
    )
    last_modified = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        self.last_modified = timezone.now()
        super().save(*args, **kwargs)

    def get_path(self, user_id):
        if self.parent_id is None:
            return '\\'
        else:
            ancestors = self.get_ancestors(include_self=True)
            if self.user_id == user_id:
                return '\\'.join(ancestors.values_list('name', flat=True))
            else:
                ancestors_list = list(ancestors)
                mount_instance = MountInstance.objects.filter(
                    share_content__folder__in=ancestors_list,
                    user_id=user_id
                ).select_related('share_content', 'mount_folder').first()
                if mount_instance:
                    while len(ancestors_list) and ancestors_list[0].id != mount_instance.share_content.folder_id:
                        ancestors_list.pop(0)

                    self_folders = mount_instance.mount_folder.get_ancestors(include_self=True)
                    self_path = '\\'.join(self_folders.values_list('name', flat=True))
                    other_path = '\\'.join([x.name for x in ancestors_list])
                    return self_path + other_path
        return

    # def __str__(self):
    #     return self.name

    class MPTTMeta:
        order_insertion_by = ['name']


class File(models.Model):
    icon_format = {
        MESSAGE_FORMAT.TEXT: '📜',
        MESSAGE_FORMAT.PHOTO: '🖼',
        MESSAGE_FORMAT.DOCUMENT: '📋',
        MESSAGE_FORMAT.AUDIO: '🔊',
        MESSAGE_FORMAT.VIDEO: '🎥',
        MESSAGE_FORMAT.GIF: '📺',
        MESSAGE_FORMAT.VOICE: '🗣',
        MESSAGE_FORMAT.VIDEO_NOTE: '🎬',
        MESSAGE_FORMAT.STICKER: '🎃',
        MESSAGE_FORMAT.LOCATION: '🗺',
        MESSAGE_FORMAT.GROUP_MEDIA: '📽'
    }

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=256,
        null=True,
        blank=True,
    )
    message_format = models.CharField(
        max_length=2,
        choices=MESSAGE_FORMAT.MESSAGE_FORMATS,
    )
    media_id = models.CharField(
        max_length=512,
    )
    datetime_change = models.DateTimeField(
        auto_now=True
    )
    folder = models.ForeignKey(
        'Folder',
        on_delete=models.CASCADE,
        related_name='files',
    )
    text = models.CharField(
        max_length=4096,
        blank=True,
        null=True
    )

    # def __str__(self):
    #     return self.name or

    def get_name(self):
        if self.name:
            show_name = self.name
        else:
            show_name = list(filter(lambda x: x[0] == self.message_format, MESSAGE_FORMAT.MESSAGE_FORMATS))[0][1]
            show_name += f' | {self.id}'

        name = f'{self.icon_format[self.message_format]} {show_name}'
        return name


    class Meta:
        ordering = ['datetime_change']


class ShareLink(models.Model):
    TYPE_SHOW_WITH_COPY = 'S'
    TYPE_SHOW_CHANGE = 'C'
    
    TYPES = (
        (TYPE_SHOW_WITH_COPY, _('Only show')),
        (TYPE_SHOW_CHANGE, _('Show and change'))
    )

    folder = models.ForeignKey(
        'Folder',
        on_delete=models.CASCADE,
        related_name='sharelinks',
        null=True,
        blank=True
    )
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name='sharelinks',
        null=True,
        blank=True
    )
    type_link = models.CharField(
        max_length=1,
        choices=TYPES
    )
    share_amount = models.IntegerField()
    share_code = models.CharField(
        max_length=64,
        unique=True
    )

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['type_link']


class MountInstance(models.Model):
    mount_folder = models.ForeignKey(
        'Folder',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    share_content = models.ForeignKey(
        ShareLink,
        on_delete=models.CASCADE,
    )
    
    class Meta:
        ordering = ['user']
