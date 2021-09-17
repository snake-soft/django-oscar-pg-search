from django.urls import path
from django.utils.translation import gettext_lazy as _
from oscar.core.application import OscarConfig


class PgSearchConfig(OscarConfig):
    label = 'search'
    name = 'oscar_pg_search'
    verbose_name = _('Search')

    namespace = 'search'

    def ready(self):
        from .views import SearchView
        self.search_view = SearchView

        #self.search_form = get_class('search.forms', 'SearchForm')

    def get_urls(self):
        #from haystack.views import search_view_factory

        # The form class has to be passed to the __init__ method as that is how
        # Haystack works.  It's slightly different to normal CBVs.
        urlpatterns = [
            path('', self.search_view.as_view(), name='search')
        ]
        return self.post_process_urls(urlpatterns)

    def get_sqs(self):
        """
        Return the SQS required by a the Haystack search view
        """
        from oscar.apps.search import facets

        return facets.base_sqs()
