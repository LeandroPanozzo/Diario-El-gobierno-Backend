# Generated by Django 5.1.1 on 2025-01-13 15:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diarioback', '0032_delete_newsreaction'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReaccionNoticia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_reaccion', models.CharField(choices=[('interesa', 'Me interesa'), ('divierte', 'Me divierte'), ('entristece', 'Me entristece'), ('enoja', 'Me enoja')], max_length=20)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('noticia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reacciones', to='diarioback.noticia')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('noticia', 'usuario')},
            },
        ),
    ]
