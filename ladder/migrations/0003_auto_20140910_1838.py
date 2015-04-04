# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        (u'ladder', u'0002_auto_20140908_0419'),
    ]

    operations = [
        migrations.RemoveField(
            model_name=u'player',
            name=u'email',
        ),
        migrations.RemoveField(
            model_name=u'player',
            name=u'home_phone',
        ),
        migrations.RemoveField(
            model_name=u'player',
            name=u'junior',
        ),
        migrations.RemoveField(
            model_name=u'player',
            name=u'mobile_phone',
        ),
        migrations.AlterField(
            model_name=u'result',
            name=u'opponent',
            field=models.ForeignKey(to=u'ladder.Player', related_name=u'result_opponent'),
        ),
        migrations.AlterField(
            model_name=u'result',
            name=u'player',
            field=models.ForeignKey(to=u'ladder.Player', related_name=u'result_player'),
        ),
    ]
