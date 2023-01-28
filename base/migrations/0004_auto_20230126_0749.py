# Generated by Django 3.1 on 2023-01-26 07:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_mountinstance_sharelink'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='file',
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='file',
            name='datetime_change',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='file',
            name='name',
            field=models.CharField(max_length=200, null=True),
        ),
    ]