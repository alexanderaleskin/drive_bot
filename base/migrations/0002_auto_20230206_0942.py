# Generated by Django 3.1 on 2023-02-06 09:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='media_id',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='file',
            name='message_format',
            field=models.CharField(choices=[('T', 'Text'), ('P', 'Image'), ('D', 'Document'), ('A', 'Audio'), ('V', 'Video'), ('G', 'GIF/animation'), ('TV', 'Voice'), ('VN', 'Video note'), ('S', 'Sticker'), ('L', 'Location'), ('GM', 'Media Group')], max_length=2),
        ),
        migrations.AlterField(
            model_name='file',
            name='name',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='file',
            name='text',
            field=models.CharField(blank=True, max_length=4096, null=True),
        ),
        migrations.AlterField(
            model_name='folder',
            name='name',
            field=models.CharField(max_length=256),
        ),
    ]
