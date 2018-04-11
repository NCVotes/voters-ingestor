# Generated by Django 2.0.4 on 2018-04-09 21:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0022_merge_20180409_2110'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filetracker',
            name='file_status',
            field=models.SmallIntegerField(choices=[(0, 'Unprocessed'), (1, 'Processing'), (2, 'Processed'), (3, 'Cancelled')], default=0, verbose_name='file status'),
        ),
    ]