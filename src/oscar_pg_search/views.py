from django.views.generic.base import TemplateView
from django.conf import settings
from oscar.apps.search.signals import user_search
from apps.catalogue.views import AjaxProductMixin, CatalogueView
from .forms import SearchForm


class SearchView(CatalogueView, AjaxProductMixin, TemplateView):
    """ This class can be splitted later to create SearchMixin for Catalogue
    Views

    This View is for following purposes:
    - Manage the submitted search form
    - filter the products by search query (SearchForm.q)
    - filter the products by facets
    """
    template_name = 'oscar/catalogue/browse.html'
    search_signal = user_search
    form_class = SearchForm
    http_method_names = ['get', ]
    results_per_page = settings.OSCAR_PRODUCTS_PER_PAGE

    def get_context_data(self, **kwargs):
        context = CatalogueView.get_context_data(self, **kwargs)
        context['summary'] = 'Suchergebnisse'
        if self.request.GET.get('q') and not context.get('products'):
            self.search_signal.send(
                sender=self, session=self.request.session,
                user=self.request.user, query=self.request.GET.get('q'))
        return context
