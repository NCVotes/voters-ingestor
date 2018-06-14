from django.test import RequestFactory, TestCase

from drilldown.templatetags.query_string import qs_trim


class QueryStringTagsTests(TestCase):
    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get('/?foo=1&bar=2')

    def test_qs_trim(self):
        self.assertEqual(qs_trim(self.request, 'foo'), 'bar=2')
        self.assertEqual(qs_trim(self.request, 'bar'), 'foo=1')

    def test_qs_trim_param_not_there(self):
        self.assertEqual(qs_trim(self.request, 'baz'), 'foo=1&bar=2')
