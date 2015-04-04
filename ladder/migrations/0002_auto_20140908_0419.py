# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        (u'ladder', u'0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name=u'player',
            name=u'junior',
            field=models.BooleanField(default=False),
        ),
    ]
