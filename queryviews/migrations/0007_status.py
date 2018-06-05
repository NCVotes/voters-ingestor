# Generated by Django 2.0.4 on 2018-06-05 13:07
import itertools

from django.db import migrations
from django.conf import settings

from matview.dbutils import make_matview_migration


class Migration(migrations.Migration):

    dependencies = [
        ('queryviews', '0006_matview_mv_voter_ncvoter_county_desc_alamance_matview_mv_voter_ncvoter_county_desc_alamance_count_ma'),
    ]

    operations = list(itertools.chain(*(
        make_matview_migration("voter.NCVoter", {}, {"voter_status_desc": code})
        for code, label, desc in settings.STATUS_CHOICES
    )))
