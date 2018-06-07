# Generated by Django 2.0.4 on 2018-06-04 16:02

from django.db import migrations, transaction
from drilldown.filters import RaceFilter


def forward(apps, schema):
    NCVoter = apps.get_model("voter.NCVoter")
    offset = 0
    limit = 10000
    q = NCVoter.objects.all()[offset:limit]
    while q:
        with transaction.atomic():
            for voter in q:
                for raceflag in RaceFilter.get_raceflags(voter=voter):
                    voter.data[raceflag] = "true"
                voter.save()
            print(".", end="", flush=True)
        offset += limit
        limit += limit
        q = NCVoter.objects.all()[offset:limit]


def backward(apps, schema):
    NCVoter = apps.get_model("voter.NCVoter")
    offset = 0
    limit = 10000
    q = NCVoter.objects.all()[offset:limit]
    while q:
        with transaction.atomic():
            for voter in q:
                for raceflag in RaceFilter.get_raceflags():
                    voter.data.pop(raceflag, None)
                voter.save()
            print(".", end="", flush=True)
        offset += limit
        limit += limit
        q = NCVoter.objects.all()[offset:limit]


class Migration(migrations.Migration):

    dependencies = [
        ('queryviews', '0006_matview_mv_voter_ncvoter_county_desc_alamance_matview_mv_voter_ncvoter_county_desc_alamance_count_ma'),
    ]

    operations = [
        migrations.RunPython(
            forward,
            backward,
        )
    ]
