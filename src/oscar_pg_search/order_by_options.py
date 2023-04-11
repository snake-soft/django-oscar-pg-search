"""
OrderByOptions are used to order the queryset just before executed on the db

Therefore it is converted to a Choice in the OrderForm
apps.search.forms.OrderForm
"""
from django.contrib.postgres.search import SearchRank, SearchQuery, SearchVector
from django.db.models import F
from oscar.core.loading import get_class

__all__ = ['OrderByOption', 'RankOrderByOption', 'PriceOrderByOption', ]

Selector = get_class('partner.strategy', 'Selector')


class OrderByOption:
    """
    This is the base class for doing every step to order the qs
    """
    def __init__(self, request_data, code, name, sort_by=None, request=None):
        self.request_data = request_data
        self.code = code
        self.name = name
        self.sort_by = sort_by
        self.request = request

    def get_ordered_qs(self, qs, query_string):
        """ This should be accessed from outside """
        return self.dispatch(qs, query_string)

    def dispatch(self, qs, query_string):
        qs = self.pre_order(qs, query_string)
        qs = self.order(qs, query_string).distinct()
        qs = self.post_order(qs, query_string)
        return qs

    def pre_union(self, qs, *args):
        """ This runs before category and product qs are merged with union """
        return qs

    def post_union(self, qs, *args):
        """ This runs before category and product qs are merged with union """
        return qs

    def pre_order(self, qs , *args):
        return qs

    def order(self, qs, *args):
        if self.sort_by:
            qs = qs.order_by(self.sort_by)
        return qs

    def post_order(self, qs, *args):
        return qs


class RankOrderByOption(OrderByOption):
    def order(self, qs, query_string, *args):
        if query_string:
            qs = qs.order_by('-rank')
        return qs

    def pre_union(self, qs, query_string, *args):
        if query_string:
            default_search_fields = [
                'title',
                'slug',
                'description',
            ]
            search_fields = getattr(
                qs.model, 'search_fields', default_search_fields
            )
            vector = SearchVector(*search_fields)
            query = SearchQuery(query_string)
            qs = qs.annotate(rank=SearchRank(vector, query))
        elif hasattr(qs.model, 'priority'):
            qs = qs.order_by('-priority', '-date_created')
        else:
            qs = qs.order_by('-date_created')
        return qs


class PriceOrderByOption(OrderByOption):
    def pre_union(self, qs, *args):
        """
        TODO: Need to make this domain agnostic!!!
        Currently it needs a strategy method to annotate the valid base price
        """
        user = getattr(self.request, 'user') if self.request else None
        strategy = Selector().strategy(request=self.request, user=user)
        if hasattr(strategy, 'annotate_price'):
            qs = strategy.annotate_price(qs)
        qs = qs.filter(base_price__isnull=False)
        return qs
