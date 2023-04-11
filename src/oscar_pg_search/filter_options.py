"""
Filters are Form fields to be passed into the Template

Every field gets an additional html class called facet_field to be executed
by JavaScript.

It should submit the form at every change.

Every Filter has two use cases:
- Create the Fields with default values
- Filter the QuerySet when the Form is posted
"""
from decimal import Decimal as D
from collections import OrderedDict
from django import forms
from django.db.models import Q
from django.conf import settings
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from oscar.core.loading import get_model

RangeProduct = get_model('offer', 'RangeProduct')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


class MultipleChoiceFieldBase(forms.MultipleChoiceField):
    widget = forms.SelectMultiple(attrs={'class': 'chosen-select'})

    def __init__(self, request_data, form, *args, request=None, **kwargs):
        super().__init__(required=False, *args, **kwargs)
        self.request_data = request_data
        self.manager = form.manager
        self.form = form
        self.request = request

    def initialize(self):
        """
        This is running after the result was created by manager.
        """
        self.choices = self.get_choices()

    @property
    def query(self):
        return self.get_query()

    def get_query(self):
        return NotImplementedError('Not implemented in subclass')

    def get_choices(self):
        return NotImplementedError('Not implemented in subclass')


class AttributeFieldBase(MultipleChoiceFieldBase):
    def __init__(self, attribute, *args, **kwargs):
        super().__init__(*args, label=attribute.name, **kwargs)
        self.attribute = attribute
        self.fieldname = f'value_{attribute.type}'


class TextAttributeField(AttributeFieldBase):
    def get_query(self):
        if str(self.attribute.id) in self.request_data:
            values_list = self.request_data.getlist(str(self.attribute.id))
            if self.attribute.type in (self.attribute.TEXT, self.attribute.FLOAT):
                values = self.attribute.productattributevalue_set.filter(
                    id__in=values_list)
                values = values.values_list(self.fieldname, flat=True)
                query_kwargs = {
                    f'attribute_values__{self.fieldname}__in': values,
                }
                return Q(**query_kwargs)
        return None

    def get_choices(self):
        """
        get value
        search first attribute with value
        """
        other_field_results_qs = self.manager.get_result(exclude=self)
        qs = self.attribute.productattributevalue_set.filter(
            product__in=other_field_results_qs)
        qs = qs.order_by(self.fieldname, 'id')
        qs = qs.distinct(self.fieldname)
        return qs.values_list('id', self.fieldname)


class MultipleChoiceAttributeField(AttributeFieldBase):
    """
    This is used as field for attribute value choices
    If one option group is used multiple times, the name and code of the 
    attributes needs to be the same!
    """
    CONVERT_CODES = ['brand', 'vessel']

    def __get_value_ids(self):
        """
        For compatibility convert some old style filter codes to new id type.
        Consider as deprecated.
        """
        if self.attribute.code in self.CONVERT_CODES \
                and self.attribute.code in self.request_data:
            result = self.request_data.getlist(self.attribute.code)
        else:
            result = self.request_data.getlist(str(self.attribute.id))
        return result

    def get_query(self):
        """
        :returns: Query for filtering the attribute_values mathching this field
        """
        values_ids = self.__get_value_ids()
        if not values_ids:
            return None
        if self.attribute.type == 'option':
            return Q(attribute_values__value_option_id__in=values_ids)
        elif self.attribute.type == 'multi_option':
            return Q(attribute_values__value_multi_option__id__in=values_ids)
        else:
            raise AttributeError('Wrong attribute type for this class')

    def get_choices(self):
        """
        Creates the choices dynamically for this attribute.
        It is calculating the results for all fields except this to offer all
        possible options by the current result.
        """
        other_field_results_qs = self.manager.get_result(exclude=self)
        if self.attribute.type == 'option':
            qs = self.attribute.option_group.options.filter(
                productattributevalue__product__in=other_field_results_qs,
            )
            qs = qs.order_by('option')
            qs = qs.distinct('option')
            return qs.values_list('id', 'option')
        elif self.attribute.type == 'multi_option':
            qs = self.attribute.option_group.options.filter(
                multi_valued_attribute_values__product__in=other_field_results_qs
            )
            qs = qs.distinct()
            qs = qs.order_by('option')
            return qs.values_list('id', 'option')
        else:
            raise AttributeError('Wrong attribute type for this class')


class ProductFieldBase(MultipleChoiceFieldBase):
    def __init__(self, code, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code = code
        self.field = Product.get_field(code)
        self.label = Product.get_field_label(self.field)

    def clean_value(self, value):
        clean_func = {
            'weight': lambda x: '{}{}'.format(
                (x * 1000).quantize(1) if x < 1 else x, 'g' if x < 1 else 'kg',
            ),
            'volume': lambda x: f'{float(x)}l',
        }.get(self.code, lambda x: x)
        return clean_func(value)

    def initialize(self):
        """
        This is running after the result was created by manager.
        """
        self.choices = self.get_choices()

    @property
    def query(self):
        return self.get_query()

    def get_query(self):
        return NotImplementedError('Not implemented in subclass')

    def get_choices(self):
        return NotImplementedError('Not implemented in subclass')


class MultipleChoiceProductField(ProductFieldBase):
    """
    This field is for weight and volume. They are attached directly to the
    Product.
    """
    def get_query(self):
        """ This is the attribute values query if this option is selected """
        option_ids = self.request_data.getlist(self.code)
        return Q(**{f'{self.code}__in': option_ids}) if option_ids else None

    def get_choices(self):
        """
        :returns: Choices drilled down by result query of all other fields.
        """
        result_for_other = self.manager.get_result(exclude=self)

        if self.field.choices:
            qs = result_for_other.order_by(self.code)
            qs = qs.distinct(self.code)
            options = qs.values_list(self.code, flat=True)
            choices = [x for x in self.field.choices if x[0] in options]
            return choices

        if self.field.related_model:
            option_qs = result_for_other.order_by().distinct(self.code)
            values = option_qs.values_list(self.code, flat=True)
            qs = self.field.related_model.objects.filter(pk__in=values)
            options = [(x.pk, str(x)) for x in qs]
            return sorted(options, key=lambda x: x[1])

        qs = result_for_other.order_by(self.code).distinct(self.code)
        options = qs.values_list(self.code, flat=True)
        result = []
        for option in options:
            if option:
                if isinstance(option, D):
                    option = option.normalize()
                result.append((option, self.clean_value(option)))
        return result


class ForeignKeyProductField(ProductFieldBase):
    widget = forms.SelectMultiple(attrs={'class': 'chosen-select'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_field = Product._meta.get_field(self.code)
        self.related_name = self.model_field.related_query_name()

    def get_query(self):
        option_ids = self.request_data.getlist(self.code)
        return Q(**{f'{self.model_field.name}__id__in': option_ids}) if option_ids else None

    def get_choices(self):
        result_for_other = self.manager.get_result(exclude=self)
        model = self.model_field.related_model

        qs_kwargs = {f'{self.related_name}__in': result_for_other}
        qs = model.objects.filter(**qs_kwargs).distinct()
        return sorted([(x.id, str(x)) for x in qs], key=lambda x: x[1])


class BooleanOfferField(forms.BooleanField):
    """
    Field that is only used for the 'Offer only' filter.
    """
    def __init__(self, request_data, form, *args, request=None, **kwargs):
        super().__init__(label='Nur Angebote', required=False, *args, **kwargs)
        self.widget.attrs={
            'onchange': 'submitFilterForm(this.form);',
            'class': 'mt-3',
        }
        self.code = 'offer_only'
        self.request_data = request_data
        self.manager = form.manager
        self.form = form
        self.choices = None
        self.request = request

    def initialize(self):
        """
        This is running after the result was created by manager.
        """
        self.choices = self.get_choices()

    def get_choices(self):
        """
        Test if this field has any choices to be selected.
        :returns: True if there are range products for this user in the result
        """
        result_for_other = self.manager.get_result(exclude=self)
        range_products = self.get_range_products()
        return result_for_other.filter(rangeproduct__in=range_products).exists()

    def get_range_products(self):
        """
        :returns: All range products for the request user.
        """
        if not self.request:
            return RangeProduct.objects.none()

        if hasattr(self.request, 'partners'):
            offers = ConditionalOffer.active.filter(
                partner__in=self.request.partners)
            qs = RangeProduct.objects.filter(
                range__condition__offers__in=offers)
            return qs

        if hasattr(RangeProduct, 'for_user'):
            return RangeProduct.for_user(self.request.user)  # @UndefinedVariable

        return RangeProduct.objects.filter(condition__range__in=offers)

    @property
    def query(self):
        """
        :returns: Query to filter the result containing only offers for this
        user when the Checkbox is checked.
        """
        if self.request_data.get('offer_only', False) == 'on':
            return Q(rangeproduct__in=self.get_range_products())
        return None


class FilterFormBase(forms.Form):
    def __init__(self, request_data, manager, qs, request=None):
        self.request_data = request_data
        self.manager = manager
        self.request = request
        self.wishlist_as_link = manager.wishlist_as_link
        self.qs = qs
        super().__init__(request_data)
        self.fields = self.get_fields()


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


FILTERS = [UserFilter, ProductFilter]
            