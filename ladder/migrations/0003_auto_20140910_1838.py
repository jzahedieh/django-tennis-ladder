# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ladder', '0002_auto_20140908_0419'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='email',
        ),
        migrations.RemoveField(
            model_name='player',
            name='home_phone',
        ),
        migrations.RemoveField(
            model_name='player',
            name='junior',
        ),
        migrations.RemoveField(
            model_name='player',
            name='mobile_phone',
        ),
        migrations.AlterField(
            model_name='result',
            name='opponent',
            field=models.ForeignKey(to='ladder.Player', related_name='result_opponent'),
        ),
        migrations.AlterField(
            model_name='result',
            name='player',
            field=models.ForeignKey(to='ladder.Player', related_name='result_player'),
        ),
    ]
