# Generated by Django 5.1.1 on 2024-09-29 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0018_alter_noticia_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='noticia',
            name='subtitulo',
            field=models.TextField(default='default content'),
        ),
    ]
