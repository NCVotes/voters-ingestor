# Generated by Django 2.0.2 on 2018-03-13 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0010_auto_20180312_1450'),
    ]

    operations = [
        migrations.CreateModel(
            name='BadLine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=255)),
                ('line_no', models.IntegerField()),
                ('line', models.TextField()),
                ('message', models.TextField()),
                ('is_warning', models.BooleanField()),
            ],
        ),
    ]