# Generated by Django 2.0.2 on 2018-03-09 14:35

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0004_auto_20180309_1431'),
    ]

    operations = [
        migrations.AddField(
            model_name='ncvoter',
            name='registr_dt',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='registr_dt'),
            preserve_default=False,
        ),
    ]