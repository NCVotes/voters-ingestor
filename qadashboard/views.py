import random

from django import forms
from django.conf import settings
from django.shortcuts import render

from voter.models import NCVoter, ChangeTracker
from matview.models import MatView
from ncvoter.known_cities import KNOWN_CITIES


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

                        "voter_status_desc": random.choice([status[0] for status in settings.STATUS_CHOICES]),
                        "race_code": random.choice([race_code[0] for race_code in settings.RACE_CHOICES]),

                        "age": random.randint(18, 90),

                        "mail_addr1": "%s DIRT RD" % random.randint(100, 900),
                        "mail_city": city,
                        "mail_zipcode": str(random.randint(20000, 29999)),
                        "res_city_desc": city,

                        "area_cd": str(random.randint(100, 999)),
                        "phone_num": str(random.randint(1000000, 9999999)),

                        "race_desc": random.choice("WHITE BLACK LATINO".split()),
                    })
                    ncid += 1
            MatView.refresh_all()
        else:
            form = ResetForm(request.POST)
            msg = "You didn't say the magic word"

    return render(request, "qadashboard.html", {
        "msg": msg,
        "reset_form": form,
    })
