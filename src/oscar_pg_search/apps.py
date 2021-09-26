from django.urls import path
from django.utils.translation import gettext_lazy as _
from oscar.core.application import OscarConfig
from oscar.core.loading import get_class


class PgSearchConfig(OscarConfig):
    label = 'search'
    name = 'oscar.apps.search'
    verbose_name = _('Search')

    namespace = 'search'

    def ready(self):
        self.search_view = get_class('catalogue.views', 'CatalogueView')

    def get_urls(self):
        urlpatterns = [
            path('', self.search_view.as_view(), name='search')
        ]
        return self.post_process_urls(urlpatterns)
