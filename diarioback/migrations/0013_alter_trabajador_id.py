# Generated by Django 5.1.1 on 2024-09-12 02:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0012_alter_noticia_imagen_cabecera'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trabajador',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
