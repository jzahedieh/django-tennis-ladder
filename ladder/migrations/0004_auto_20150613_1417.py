# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ladder', '0003_auto_20140910_1838'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ladder',
            name='division',
            field=models.IntegerField(max_length=11),
        ),
    ]
