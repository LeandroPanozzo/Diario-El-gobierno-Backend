# Generated by Django 5.1.1 on 2024-09-27 18:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0017_noticia_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='noticia',
            name='slug',
            field=models.SlugField(blank=True, editable=False, unique=True),
        ),
    ]
