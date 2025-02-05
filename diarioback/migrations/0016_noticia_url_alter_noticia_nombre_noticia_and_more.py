# Generated by Django 5.1.1 on 2024-09-23 01:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0015_remove_rol_trabajadores_remove_trabajador_contraseña_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='noticia',
            name='url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='noticia',
            name='nombre_noticia',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='rol',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
