# Generated by Django 2.0.4 on 2018-05-25 19:31
import itertools

from django.db import migrations
from django.conf import settings

from matview.dbutils import make_matview_migration


class Migration(migrations.Migration):

    dependencies = [
        ('queryviews', '0004_matview_mv_voter_ncvoter_count_matview_mv_voter_ncvoter_gender_code_f_matview_mv_voter_ncvoter_gende'),
    ]

    operations = list(itertools.chain(*(
        make_matview_migration("voter.NCVoter", {}, {"county_desc": county})
        for county in settings.COUNTIES
    )))
