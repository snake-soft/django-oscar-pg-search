"""
The PostgresSearchHandler class is loaded by apps.catalogue.search_handlers
"""
import re
from django.conf import settings
from django.db import models
from django.contrib.postgres.search import TrigramSimilarity, SearchQuery,\
    SearchRank, SearchVector
from django.db.models import Q, F, ExpressionWrapper
from django.utils.safestring import mark_safe
from django.db.models.functions.comparison import Coalesce

from oscar.apps.catalogue.search_handlers import SimpleProductSearchHandler
from oscar.core.loading import get_model

from .forms import SearchForm, OrderForm
from .utils import FilterManager

Product = get_model('catalogue', 'Product')
Category = get_model('catalogue', 'Category')


class PostgresSearchHandler(SimpleProductSearchHandler):
    search_fields = ['title', 'slug', 'description']
    search_form_class = SearchForm
    order_form_class = OrderForm

    def __init__(self, request, request_data, full_path, categories=None):
        self.request = request
        self.request_data = request_data

        self.search_form = self.search_form_class(request_data)
        self.query_string = self.search_form.get_query_string()

        self.order_form = self.order_form_class(request, request_data)
        self.order_by_option = self.order_form.get_sort_by()

        super().__init__(request_data, full_path, categories)

    @property
    def vector(self):
        return SearchVector('title', weight='A')\
            + SearchVector('description', weight='C')

    @property
    def query(self):
        return SearchQuery(self.query_string)

    @property
    def rank(self):
        return SearchRank(self.vector, self.query)

    @property
    def paginate_by(self):
        if self.request_data.get('format') == 'ajax':
            return settings.OSCAR_PRODUCTS_PER_PAGE_AJAX
        return settings.OSCAR_PRODUCTS_PER_PAGE

    def get_queryset(self, unfiltered=False):
        if hasattr(Product, 'for_user'):
            qs = Product.for_user(self.request.user)
        else:
            qs = Product.objects.browsable()

        query_string = self.query_string
        if not self.categories:
            if query_string:
                self.categories = self.search_categories(query_string)
            else:
                self.categories = Category.objects.browsable()

        if self.order_by_option:
            qs = self.order_by_option.pre_union(qs, query_string)

        qs = self.search(qs, query_string)

        self.filter_manager = FilterManager(self.request, qs)
        qs = self.filter_manager.result

        if self.order_by_option:
            qs = self.order_by_option.post_union(qs, query_string)
            qs = self.order_by_option.get_ordered_qs(qs, self.query_string)

        return qs

    def get_context_data(self, *, object_list=None, **kwargs):
        context = SimpleProductSearchHandler.get_context_data(self, **kwargs)
        search_params = ''
        if self.query_string:
            search_params += '&q=' + self.query_string
        if self.order_by_option:
            search_params += '&sort_by=' + self.order_by_option.code
        context['search_params'] = mark_safe(search_params)
        context['filter_forms'] = self.filter_manager.filters
        return context

    def get_search_context_data(self, context_object_name):
        self.context_object_name = context_object_name
        context = self.get_context_data(object_list=self.object_list)
        self.get_context_data(object_list=self.object_list.filter(id=0))
        if context['page_obj']:
            context[context_object_name] = context['page_obj'].object_list
        else:
            context[context_object_name] = self.object_list.filter(id=0)
        return context

    def search(self, qs, query_string):
        return self.search_products(qs, query_string)

    def search_products(self, qs, query_string):
        if query_string:
            qs = qs.annotate(
                upc_rank=Coalesce(
                    TrigramSimilarity('upc', query_string), 0,
                    output_field=models.DecimalField(),
                ),
            )
            qs = qs.annotate(
                title_rank=Coalesce(
                    TrigramSimilarity('title', query_string), 0,
                    output_field=models.DecimalField(),
                ),
            )
            qs = qs.annotate(
                meta_description_rank=Coalesce(
                    TrigramSimilarity('meta_description', query_string), 0,
                    output_field=models.DecimalField(),
                ),
            )
            qs = qs.annotate(
                meta_title_rank=Coalesce(
                    TrigramSimilarity('meta_title', query_string), 0,
                    output_field=models.DecimalField(),
                ),
            )
            qs = qs.annotate(
                rank=ExpressionWrapper(
                    F('upc_rank')
                    + F('title_rank')
                    + F('meta_description_rank') * 2
                    + F('meta_title_rank') * 2,
                    output_field=models.DecimalField(),
                ),
            )
            qs = qs.filter(Q(rank__gt=0.1) | Q(categories__in=self.categories))
            return qs
        else:
            return qs.filter(Q(categories__in=self.categories))

    def search_categories(self, query_string):
        """ Return categories that contain query_string """
        qs = Category.objects.browsable()
        qs = qs.annotate(
            name_rank=Coalesce(
                TrigramSimilarity('name', query_string), 0,
                output_field=models.DecimalField(),
            ),
        )
        qs = qs.annotate(
            description_rank=Coalesce(
                TrigramSimilarity('description', query_string), 0,
                output_field=models.DecimalField(),
            )
        )
        qs = qs.annotate(
            meta_description_rank=Coalesce(
                TrigramSimilarity('meta_description', query_string), 0,
                output_field=models.DecimalField(),
            )
        )
        qs = qs.annotate(
            meta_title_rank=Coalesce(
                TrigramSimilarity('meta_title', query_string), 0,
                output_field=models.DecimalField(),
            ),
        )
        qs = qs.annotate(
            rank=ExpressionWrapper(
                F('name_rank')
                + F('meta_description_rank')
                + F('meta_title_rank') * 2
                + F('description_rank'),
                output_field=models.DecimalField(),
            )
        )
        qs = qs.filter(rank__gte=0.17).order_by('depth', '-rank')
        category = qs.first()
        if category:
            return category.get_descendants_and_self()
        return []

    def union(self, *args):
        query_string = self.query_string
        qs_arr = []
        for qs in args:
            if self.order_by_option:
                qs = self.order_by_option.pre_union(qs, query_string)
            qs_arr.append(qs)

        if qs_arr:
            qs = args[0].union(*qs_arr[1:])
            if self.order_by_option:
                qs = self.order_by_option.post_union(qs, query_string)
            return qs

    @classmethod
    def normalize_query(cls, query_string,
                        findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                        normspace=re.compile(r'\s{2,}').sub):
        ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
            and grouping quoted words together.
            Example:

            >>> normalize_query('  some random  words "with   quotes  " and   spaces')
            ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
        https://www.julienphalip.com/blog/adding-search-to-a-django-site-in-a-snap/
        '''
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

    @classmethod
    def str_to_query(cls, search_str, search_fields):
        query = None # Query to search for every search term        
        terms = cls.normalize_query(search_str)
        for term in terms:
            or_query = None # Query to search for a given term in each field
            for field_name in search_fields:
                q = Q(**{"%s__icontains" % field_name: term})
                if or_query is None:
                    or_query = q
                else:
                    or_query = or_query | q
            if query is None:
                query = or_query
            else:
                query = query & or_query
        return query
