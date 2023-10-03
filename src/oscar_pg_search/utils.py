""" FilterManager for search filters """
from .filter_options import FILTERS


class FilterManager:
    """
    This is the interface to all search filters.
    :param request: Request of the search
    :param qs: Product objects may be prefiltered by search or user rules
    """
    fltr_cls = FILTERS
    wishlist_as_link = False

    def __init__(self, request_data, qs, request=None):
        self.request = request
        self.request_data = request_data
        self.qs = qs

        # Domain specific logic for creating Partner based options:
        if request and hasattr(request, 'partners'):
            self.main_partner = getattr(request, 'partners')[0]
            self.wishlist_as_link = self.main_partner.wishlist_as_link
        self.filters = self.get_filters(request=request)
        self.result = self.get_result()
        self.initialize_filters()

    def get_filters(self, **kwargs):
        """
        :returns: All filter instances
        """
        fltrs = []
        for _cls in self.fltr_cls:
            fltr = _cls(self.request_data, self, self.qs, **kwargs)
            fltrs.append(fltr)
        return fltrs

    def get_queries(self, exclude=None):
        """
        :returns: List of all queries from the filters to be combined
        """
        queries = []
        for fltr in self.filters:
            for query in fltr.queries:
                if exclude is None or exclude.query != query:
                    queries.append(query)
        return queries

    def get_result(self, exclude=None):
        """
        :returns: Result Queryset filtered by all filters
        """
        qs = self.qs
        for query in self.get_queries(exclude=exclude):
            if query is not None:
                qs = qs.filter(query)
        return qs

    def initialize_filters(self):
        """
        We need to initialize the filters after creating the results because
        many filters have choices that depend on the result.
        """
        for fltr in self.filters:
            fltr.initialize()
