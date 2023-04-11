from collections import defaultdict
from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms.widgets import Input
from django.http.request import QueryDict
from .order_by_options import *


class SearchInput(Input):
    """
    Defining a search type widget

    This is an HTML5 thing and works nicely with Safari, other browsers default
    back to using the default "text" type
    """
    input_type = 'search'


# Build a dict of valid queries
VALID_FACET_QUERIES = defaultdict(list)
for facet in settings.OSCAR_SEARCH_FACETS['queries'].values():
    field_name = "%s_exact" % facet['field']
    queries = [t[1] for t in facet['queries']]
    VALID_FACET_QUERIES[field_name].extend(queries)


class OrderForm(forms.Form):
    sort_by = forms.ChoiceField(
        label=_("Sort by"), choices=[],
        widget=forms.Select(), required=False)
    sort_by.widget.attrs.update({'onchange': 'submitOrderForm(this.form);'})

    def __init__(self, request_data, *args, request=None, **kwargs):
        assert isinstance(request_data, QueryDict)
        self.request_data = request_data
        self.request = request
        super().__init__(request_data, *args, **kwargs)
        self.fields['sort_by'].choices = self.get_sort_by_choices()

    @property
    def choice_objects(self):
        return [
            RankOrderByOption(
                self.request_data,
                'relevancy',
                _('Relevancy'),
                '-rank',
                request=self.request,
            ),
            OrderByOption(
                self.request_data,
                'newest',
                'Neuste Artikel',
                '-date_created',
                request=self.request,
            ),
            OrderByOption(
                self.request_data,
                'updated',
                'Letzte Änderungen',
                '-date_updated',
                request=self.request,
            ),
            OrderByOption(
                self.request_data,
                'title-asc',
                _('Title A to Z'),
                'title',
                request=self.request,
            ),
            OrderByOption(
                self.request_data,
                'title-desc',
                _('Title Z to A'),
                '-title',
                request=self.request,
            ),
        ]

    @property
    def choice_objects_with_price(self):
        return [
            PriceOrderByOption(
                self.request_data,
                'price-asc',
                _('Price low to high'),
                'base_price',
                request=self.request,
            ),
            PriceOrderByOption(
                self.request_data,
                'price-desc',
                _('Price high to low'),
                '-base_price',
                request=self.request,
            ),
        ]

    def get_sort_by_choices(self):
        options = self.choice_objects
        if self.request and not getattr(self.request.user, 'hide_price', False):
            options += self.choice_objects_with_price
        return ((choice.code, choice.name) for choice in options)

    def get_sort_by(self):
        if self.is_valid():
            sort_by = self.cleaned_data.get('sort_by')
            for choice in self.choice_objects + self.choice_objects_with_price:
                if choice.code == sort_by:
                    return choice
        return self.choice_objects[0]


class SearchForm(forms.Form):
    """
    In Haystack, the search form is used for interpreting
    and sub-filtering the SQS.
    """
    # Use a tabindex of 1 so that users can hit tab on any page and it will
    # focus on the search widget.
    q = forms.CharField(
        empty_value='',
        required=False, label=_('Search'),
        widget=SearchInput({
            "placeholder": _('Search'),
            "tabindex": "1",
            "class": "form-control"
        }))

    def __init__(self, request_data, *args, **kwargs):
        if request_data.get('q') == 'None':
            request_data = dict(request_data)
            del request_data['q']
        super().__init__(request_data, *args, **kwargs)
        self.fields['q'].widget.attrs['placeholder'] = 'Suche'
        self.fields['q'].widget.attrs['id'] = 'search_form_input'
        self.fields['q'].widget.attrs['class'] = 'form-control'
        self.fields['q'].widget.attrs['name'] = 'q'
        self.fields['q'].widget.attrs['aria-label'] = "Search"

    def get_query_string(self):
        if self.is_valid():  # BUG?
            query_string = self.cleaned_data.get('q', '')
            if query_string != 'None':
                return self.clean_query_string(query_string)

    @staticmethod
    def clean_query_string(query_string):
        if query_string:
            return query_string.replace(',', '.')
