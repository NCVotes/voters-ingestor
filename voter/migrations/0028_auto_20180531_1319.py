# Generated by Django 2.0.4 on 2018-05-31 13:19

import django.contrib.postgres.indexes
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0027_auto_20180417_1418'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='ncvoter',
            index=django.contrib.postgres.indexes.GinIndex(fields=['data'], name='voter_ncvot_data_2e8e15_gin'),
        ),
    ]