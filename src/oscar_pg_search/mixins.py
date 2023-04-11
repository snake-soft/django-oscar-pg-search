from django.conf import settings
from oscar.apps.search.signals import user_search
from django.utils.module_loading import import_string
from .forms import SearchForm, OrderForm


class SearchViewMixin:
    """
    This should be included in all sites with sort functionality
    Most likely this would be CatalogueView and ProductCategoryView
    """

    template_name = 'oscar/catalogue/browse.html'
    search_signal = user_search
    form_class = SearchForm
    http_method_names = ['get', ]
    results_per_page = settings.OSCAR_PRODUCTS_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_form'] = OrderForm(
            self.request.GET,
            request=self.request,
        )
        context['summary'] = 'Suchergebnisse'
        if self.request.GET.get('q') and not context.get('products'):
            self.search_signal.send(
                sender=self, session=self.request.session,
                user=self.request.user, query=self.request.GET.get('q'))
        return context

    def get_search_handler(self, *args, **kwargs):
        """ Need request in the search handler """
        search_handler_class = import_string(
            settings.OSCAR_PRODUCT_SEARCH_HANDLER
        )
        return search_handler_class(*args, request=self.request, **kwargs)
