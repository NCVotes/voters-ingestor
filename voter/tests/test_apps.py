from django.apps import apps
from django.test import TestCase

from voter.apps import VoterConfig


class VoterAppTest(TestCase):

    def test_app_config(self):
        self.assertEqual(VoterConfig.name, 'voter')
        self.assertEqual(apps.get_app_config('voter').name, 'voter')
