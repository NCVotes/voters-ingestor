# Generated by Django 2.0.4 on 2018-05-17 20:23
import itertools

from django.db import migrations
from matview.dbutils import make_matview_migration


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0001_initial'),
        ('matview', '0001_initial'),
    ]

    operations = itertools.chain(*(
        make_matview_migration("voter.NCVoter", None, {"sex_code": "F"}),
        make_matview_migration("voter.NCVoter", None, {"sex_code": "M"}),
    ))
