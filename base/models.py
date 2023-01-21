from django.db import models
from telegram_django_bot.models import TelegramUser


class User(TelegramUser):
    pass


class Folder(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='folders',
        verbose_name='Пользователь'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Родительская папка'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название папки'
    )
    date_change = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата изменения папки'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Папка'
        verbose_name_plural = 'Папки'
        ordering = ['name']


class File(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    message_format = models.CharField(
        max_length=200,
        verbose_name='Формат файла',
    )
    media_id = models.CharField(
        max_length=1000,
        verbose_name='Файл'
    )
    folder = models.ForeignKey(
        'Folder',
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='Папка'
    )
    text = models.CharField(
        default='Заметка',
        max_length=150,
        verbose_name='Заметки к файлу',
        blank=True,
        null=True
    )

    def __str__(self):
        return f'{self.media_id} - {self.text}'

    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'
        ordering = ['media_id']
