import factory


class NCVoter(factory.django.DjangoModelFactory):
    class Meta:
        model = 'voter.NCVoter'


class NCVoterQueryCache(factory.django.DjangoModelFactory):
    class Meta:
        model = 'voter.NCVoterQueryCache'
