# Generated by Django 2.0.2 on 2018-03-21 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0014_auto_20180319_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changetracker',
            name='op_code',
            field=models.CharField(choices=[('A', 'Add'), ('M', 'Modify')], db_index=True, max_length=1, verbose_name='Operation Code'),
        ),
    ]
