# Generated by Django 2.0.4 on 2018-04-17 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0026_merge_20180417_1417'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changetracker',
            name='op_code',
            field=models.CharField(choices=[('A', 'Add'), ('M', 'Modify')], db_index=True, max_length=1, verbose_name='Operation Code'),
        ),
    ]
