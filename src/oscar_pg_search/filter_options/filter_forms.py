from collections import OrderedDict
from django import forms
from django.db.models import Q
from django.conf import settings
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from oscar.core.loading import get_model
from .base_form import FilterFormBase
from .product_fields import MultipleChoiceProductField
from .offer_fields import BooleanOfferField
from .attribute_fields import TextAttributeField, MultipleChoiceAttributeField


RangeProduct = get_model('offer', 'RangeProduct')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


class ProductFilter(FilterFormBase):
    """
    This filter has three kinds of fields:
    - MultipleChoiceAttributeField for dynamic attribute value fields
    - MultipleChoiceProductField for product attached data (weight, volume)
    - BooleanOfferField for filtering offers only
    """
    name = 'Filter'
    code = 'filter'
    disabled_fields = getattr(settings, 'OSCAR_SEARCH_DISABLED_FIELDS', [])

    def initialize(self):
        """
        Initializes all fields after the first result was calculated.
        It is executed by the FilterManager from outside
        """
        delete_fields = []
        for fieldname, field in self.fields.items():
            if hasattr(field, 'initialize'):
                field.initialize()
                if not field.choices:
                    delete_fields.append(fieldname)
        result = self.is_valid()
        self._errors = {}
        for fieldname in delete_fields:
            del self.fields[fieldname]
        return result

    @property
    def enabled_attached_fields(self):
        codes = getattr(settings, 'OSCAR_ATTACHED_PRODUCT_FIELDS', [])
        return [x for x in codes if x not in self.disabled_fields]

    def get_product_fields(self):
        """
        :returns: Newly created MultipleChoiceProductField's (volume, weight)
        """
        fields = {}
        for code in self.enabled_attached_fields:
            fields[code] = MultipleChoiceProductField(code, self.request_data, self)
        return fields

    def get_offer_field(self):
        """
        :returns: BooleanOfferField for offer_only filter
        """
        field = BooleanOfferField(self.request_data, self)
        if field.get_range_products().exists():
            return {'offer_only': field}
        return {}

    @property
    def enabled_attributes(self):
        qs = ProductAttribute.objects.all()
        if ProductAttribute._meta.get_field('filter_enabled'):
            qs = qs.filter(filter_enabled=True)
        codes = qs.values_list('code', flat=True)
        return {x for x in codes if x not in self.disabled_fields}

    def get_attribute_fields(self):
        """
        :returns: MultipleChoiceAttributeField for dynamic attribute values
        """
        fields = {}
        qs = ProductAttribute.objects.exclude(code__in=self.disabled_fields)
        if hasattr(ProductAttribute, 'filter_enabled'):
            qs = qs.filter(filter_enabled=True)
        qs = qs.filter(productattributevalue__product__in=self.qs)
        qs = qs.order_by('name', 'option_group_id')
        qs = qs.distinct('name', 'option_group_id')
        for attribute in qs:
            if self.enabled_attributes \
                    and attribute.code not in self.enabled_attributes:
                continue

            if attribute.type in (attribute.TEXT, attribute.FLOAT):
                field = TextAttributeField(attribute, self.request_data, self)
            elif attribute.type in (attribute.OPTION, attribute.MULTI_OPTION):
                field = MultipleChoiceAttributeField(
                    attribute, self.request_data, self)
            else:
                raise NotImplementedError('Other fields need to be created')
            fields[str(attribute.id)] = field
        return fields

    def get_fields(self):
        """
        :returns: Resorted fields containing the new created.
        """
        fields = OrderedDict(
            **self.get_offer_field(),
            **self.get_product_fields(),
            **self.fields,
            **self.get_attribute_fields(),
        )
        return fields

    @property
    def queries(self):
        """
        :returns: All queries of this filter.
        """
        queries = []
        for field in self.fields.values():
            if hasattr(field, 'query') and field.query is not None:
                queries.append(field.query)
        return queries


class UserFilter(FilterFormBase):
    """
    This filter needs the user to be authenticated.
    It manages two fields with a very similar logic:
    - wishlist
    - order
    """
    name = 'Mein Shop'
    code = 'user'
    disabled_fields = getattr(settings, 'OSCAR_SEARCH_DISABLED_FIELDS', [])

    def get_fields(self):
        fields = {}
        if self.wishlist_as_link:
            url = reverse('customer:wishlists-list')
            onchange_js = 'var key = $(this).val(); window.location.replace'\
                f'("{url}" + key);'
            fields['wishlist'] = forms.MultipleChoiceField(
                label='Favoritenlisten',
                widget=forms.Select(
                    attrs={'onchange': onchange_js}),
                required=False,
            )
        else:
            fields['wishlist'] = forms.MultipleChoiceField(
                label='Favoritenlisten',
                widget=forms.SelectMultiple(attrs={'class': 'chosen-select'}),
                required=False,
            )

        fields['order'] = forms.MultipleChoiceField(
            label='Vorherige Bestellungen',
            widget=forms.SelectMultiple(attrs={'class': 'chosen-select'}),
            required=False,
        )
        return fields

    def initialize(self):
        """
        Initializes all fields after the first result was calculated.
        It is executed by the FilterManager from outside.
        This filter needs the user to be authenticated.
        """
        if not self.request or not self.request.user.is_authenticated:
            self.fields = {}
            return None

        if 'wishlist' in self.fields:
            self.fields['wishlist'].choices = self.get_wishlist_choices()

        if 'order' in self.fields:
            self.fields['order'].choices = self.get_order_choices()
        result = self.is_valid()
        self._errors = {}
        return result

    def get_wishlist_choices(self):
        """
        :returns: All wishlists of request user as choices.
        """
        if not self.request:
            return []

        if self.wishlist_as_link:
            return [
                ('', _('zur Liste springen')),
                *self.request.user.wishlists.values_list('key', 'name')
            ]
        return self.request.user.wishlists.values_list('id', 'name')

    def get_order_choices(self):
        """
        :returns: All orders of request user as choices.
        """
        if not self.request:
            return []

        order_choices = []
        order_tuples = self.request.user.orders.values_list(
            'id', 'number', 'date_placed'
        )
        for id_, number, date_placed in order_tuples:
            order_choices.append((id_, f'{number} ({date_placed.date()})'))
        return order_choices

    @property
    def queries(self):
        """
        :returns: All queries of this filter. It combines them with or to be
        able to combine both fields.
        """
        query = Q()

        if 'wishlist' in self.request_data:
            wishlist_ids = self.request_data.getlist('wishlist')
            query |= Q(wishlists_lines__wishlist_id__in=wishlist_ids)

        if 'order' in self.request_data:
            order_ids = self.request_data.getlist('order')
            query |= Q(line__order_id__in=order_ids)

        return [query]
