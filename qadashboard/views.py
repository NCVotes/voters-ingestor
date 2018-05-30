from django import forms
from django.shortcuts import render

from voter.models import NCVoter, ChangeTracker
from matview.models import MatView


class ResetForm(forms.Form):
    confirmation = forms.CharField(help_text="Are you sure?")
    voter_config = forms.CharField(widget=forms.Textarea)


def qadashboard(request):
    msg = None
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
                    NCVoter.objects.create(ncid=str(ncid), data={
                        "first_name": "FIRST%s" % (ncid,),
                        "last_name": lasts[i % len(lasts)],
                        "party_cd": 'DEM' if party.lower().startswith('d') else 'REP',
                        "gender_code": gender.upper()[0],
                        "county_desc": county,
                    })
                    ncid += 1
            MatView.refresh_all()
        else:
            msg = "You didn't say the magic word"

    return render(request, "qadashboard.html", {
        "msg": msg,
        "reset_form": ResetForm(),
    })
