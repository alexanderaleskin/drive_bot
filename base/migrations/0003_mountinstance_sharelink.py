# Generated by Django 3.1 on 2023-01-25 08:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_auto_20230123_1111'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShareLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_link', models.CharField(choices=[('S', 'show with copy'), ('C', 'show and change')], max_length=1)),
                ('share_amount', models.IntegerField()),
                ('share_code', models.CharField(max_length=64, unique=True)),
                ('file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sharelinks', to='base.file')),
                ('folder', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sharelinks', to='base.folder')),
            ],
            options={
                'ordering': ['type_link'],
            },
        ),
        migrations.CreateModel(
            name='MountInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mount_folder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.folder')),
                ('share_content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.sharelink')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user'],
            },
        ),
    ]