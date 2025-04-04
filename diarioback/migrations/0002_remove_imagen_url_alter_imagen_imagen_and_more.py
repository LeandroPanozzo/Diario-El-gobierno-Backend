# Generated by Django 5.1.1 on 2024-09-07 02:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='imagen',
            name='url',
        ),
        migrations.AlterField(
            model_name='imagen',
            name='imagen',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='noticia',
            name='imagen_cabecera',
            field=models.URLField(),
        ),
        migrations.AlterField(
            model_name='trabajador',
            name='foto_perfil',
            field=models.URLField(),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='foto_perfil',
            field=models.URLField(),
        ),
    ]
