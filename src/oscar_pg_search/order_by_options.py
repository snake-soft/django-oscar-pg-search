"""
OrderByOptions are used to order the queryset just before executed on the db

Therefore it is converted to a Choice in the OrderForm
apps.search.forms.OrderForm
"""
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.search import SearchRank, SearchQuery
from django.db.models.aggregates import Min
from django.db.models import Q, When, Case, Value, BooleanField

__all__ = ['OrderByOption', 'RankOrderByOption', 'PriceOrderByOption', ]


class OrderByOption:
    """
    This is the base class for doing every step to order the qs
    """
    def __init__(self, code, name, sort_by=None):
        self.code = code
        self.name = name
        self.sort_by = sort_by

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
            vector = qs.model.get_search_vector()
            query = SearchQuery(query_string)
            qs = qs.annotate(rank=SearchRank(vector, query))
        else:
            qs = qs.order_by('-priority', '-date_created')
        return qs


class PriceOrderByOption(OrderByOption):

    def pre_union(self, qs, *args):
        """
        TODO:
        When specialprice and specialprice_start < now < specialprice_end
        When id in with_special_price
            price = specialprice
        else 
            price = Min('stockrecords__price')
        """
        return qs.annotate(price=Min('stockrecords__price'))
