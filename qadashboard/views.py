import random

from django import forms
from django.shortcuts import render

from ncvoter.known_cities import KNOWN_CITIES
from voter.constants import STATUS_FILTER_CHOICES, RACE_FILTER_CHOICES, COUNTIES
from voter.models import NCVoter, ChangeTracker, NCVoterQueryView


class ResetForm(forms.Form):
    confirmation = forms.CharField(help_text="Are you sure?")
    voter_config = forms.CharField(widget=forms.Textarea)


def qadashboard(request):
    msg = None
    form = ResetForm()

    if request.method == 'POST':
        confirmation = request.POST.get('confirmation')
        if confirmation == 'YES':
            NCVoter.objects.all().delete()
            ChangeTracker.objects.all().delete()

            lines = [l.split() for l in request.POST.get('voter_config').split('\n')]
            ncid = 1
            lasts = "ABCDEFGH"
            for county, party, gender, count in lines:
                for i in range(int(count)):
                    city = random.choice(KNOWN_CITIES)
                    NCVoter.objects.create(ncid=str(ncid), data={
                        "first_name": "FIRST%s" % (ncid,),
                        "midl_name": lasts[i % len(lasts)],
                        "last_name": lasts[i % len(lasts)],

                        "party_cd": 'DEM' if party.lower().startswith('d') else 'REP',
                        "gender_code": gender.upper()[0],

                        "county_desc": county.upper(),
                        "county_id": COUNTIES.index(county.upper()) + 1,

                        "status_cd": random.choice([status[0] for status in STATUS_FILTER_CHOICES]),

                        "race_code": random.choice([race_code[0] for race_code in RACE_FILTER_CHOICES]),
                        "ethnic_code": 'UN' if random.random() < 0.03 else 'HL',  # ~3% Hispanic voters

                        "age": random.randint(18, 90),

                        "res_street_address": "%s DIRT RD" % random.randint(100, 900),
                        "res_city_desc": city,
                        "zip_code": str(random.randint(20000, 29999)),

                        "area_cd": str(random.randint(100, 999)),
                        "phone_num": str(random.randint(1000000, 9999999)),
                    })
                    ncid += 1
            NCVoterQueryView.refresh()
        else:
            form = ResetForm(request.POST)
            msg = "You didn't say the magic word"

    return render(request, "qadashboard.html", {
        "msg": msg,
        "reset_form": form,
    })
