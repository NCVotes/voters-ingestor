# Generated by Django 2.0.2 on 2018-03-19 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0013_auto_20180319_1445'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changetracker',
            name='file_lineno',
            field=models.IntegerField(db_index=True, default=-1),
            preserve_default=False,
        ),
    ]
