# Generated by Django 5.1.1 on 2024-10-04 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0022_alter_noticia_seccion1_alter_noticia_seccion2_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estadopublicacion',
            name='nombre_estado',
            field=models.CharField(choices=[('borrador', 'Borrador'), ('en_papelera', 'En Papelera'), ('publicado', 'Publicado'), ('listo_para_editar', 'Listo para editar')], default='borrador', max_length=20),
        ),
    ]
