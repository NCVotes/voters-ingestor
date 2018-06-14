from django.apps import apps
from django.test import TestCase

from drilldown.apps import DrilldownConfig


class DrilldownAppTest(TestCase):

    def test_app_config(self):
        self.assertEqual(DrilldownConfig.name, 'drilldown')
        self.assertEqual(apps.get_app_config('drilldown').name, 'drilldown')
