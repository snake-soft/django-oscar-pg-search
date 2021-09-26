from django.test.testcases import TestCase
from oscar_pg_search.postgres_search_handler import PostgresSearchHandler


class TestSearchHandler(TestCase):
    def test_instance(self):
        self.assertEqual(True, True)
