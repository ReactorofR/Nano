# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='QtAnimeGirl',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=40, blank=True)),
                ('elo', models.IntegerField(default=1000)),
                ('image', models.CharField(max_length=100, unique=True)),
            ],
        ),
    ]
