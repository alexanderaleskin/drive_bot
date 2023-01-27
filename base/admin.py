from django.contrib import admin

from .models import User, File, Folder, MountInstance, ShareLink

admin.site.register(MountInstance)
admin.site.register(ShareLink)


@admin.register(Folder)
class AdminFolder(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'parent')
    list_filter = ('user', 'name')


@admin.register(User)
class AdminUser(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name')
    list_filter = ('first_name', 'last_name')


@admin.register(File)
class AdminFile(admin.ModelAdmin):
    list_display = ('id', 'media_id', 'text', 'folder')
    list_filter = ('media_id', 'folder')
