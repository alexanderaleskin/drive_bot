from telegram_django_bot.models import TelegramUser
from django.db import models


class User(TelegramUser):
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Folder.objects.get_or_create(
            user=self,
            parent=None,
            name='',
        )


class Folder(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='folders',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(
        max_length=200,
    )
    datetime_change = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class File(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    message_format = models.CharField(
        max_length=200,
    )
    media_id = models.CharField(
        max_length=1000,
    )
    folder = models.ForeignKey(
        'Folder',
        on_delete=models.CASCADE,
        related_name='files',
    )
    text = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    def __str__(self):
        return f'{self.media_id} - {self.text}'

    class Meta:
        ordering = ['media_id']
