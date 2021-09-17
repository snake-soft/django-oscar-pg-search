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
from django import forms
from django.db.models import Q
from oscar.core.loading import get_model

RangeProduct = get_model('offer', 'RangeProduct')
ProductAttribute = get_model('catalogue', 'ProductAttribute')


class MultipleChoiceAttributeField(forms.MultipleChoiceField):
    """
    This is used as field for attribute value choices
    If one option group is used multiple times, the name and code of the 
    attributes needs to be the same!
    """
    widget = forms.SelectMultiple(attrs={'class': 'chosen-select'})
    CONVERT_CODES = ['brand', 'vessel']

    def __init__(self, attribute, request, form, *args, **kwargs):
        super().__init__(label=attribute.name, required=False, *args, **kwargs)
        self.attribute = attribute
        self.request = request
        self.manager = form.manager
        self.form = form

    def initialize(self):
        """
        This is running after the result was created by manager.
        """
        self.choices = self.get_choices()

    def __get_value_ids(self):
        """
        For compatibility convert some old style filter codes to new id type.
        Consider as deprecated.
        """
        if self.attribute.code in self.CONVERT_CODES \
                and self.attribute.code in self.request.GET:
            result = self.request.GET.getlist(self.attribute.code)
        else:
            result = self.request.GET.getlist(str(self.attribute.id))
        return result

    @property
    def query(self):
        """
        :returns: Query for filtering the attribute_values mathching this field
        """
        values_ids = self.__get_value_ids()
        return Q(attribute_values__value_option_id__in=values_ids) \
            if values_ids else None

    def get_choices(self):
        """
        Creates the choices dynamically for this attribute.
        It is calculating the results for all fields except this to offer all
        possible options by the current result.
        """
        other_field_results_qs = self.manager.get_result(exclude=self)
        qs = self.attribute.option_group.options.filter(
            productattributevalue__product__in=other_field_results_qs,
        )
        qs = qs.order_by('option')
        qs = qs.distinct('option')
        return qs.values_list('id', 'option')


class MultipleChoiceProductField(forms.MultipleChoiceField):
    """
    This field is for weight and volume. They are attached directly to the
    Product.
    """
    widget = forms.SelectMultiple(attrs={'class': 'chosen-select'})

    def __init__(self, code, request, form, label_funct, *args, **kwargs):
        super().__init__(required=False, *args, **kwargs)
        self.request = request
        self.manager = form.manager
        self.label_funct = label_funct
        self.code = code

    def initialize(self):
        """
        This is running after the result was created by manager.
        """
        self.choices = self.get_choices()

    @property
    def query(self):
        """ This is the attribute values query if this option is selected """
        option_ids = self.request.GET.getlist(self.code)
        return Q(**{f'{self.code}__in': option_ids}) if option_ids else None

    def get_choices(self):
        """
        :returns: Choices drilled down by result query of all other fields.
        """
        result_for_other = self.manager.get_result(exclude=self)
        options = set(result_for_other.values_list(self.code, flat=True))
        result = []
        for option in options:
            if option:
                if isinstance(option, D):
                    option = option.normalize()
                result.append((option, self.label_funct(option)))
        return sorted(result)


class BooleanOfferField(forms.BooleanField):
    """
    Field that is only used for the 'Offer only' filter.
    """
    def __init__(self, request, form, *args, **kwargs):
        super().__init__(label='Nur Angebote', required=False, *args, **kwargs)
        self.widget.attrs={
            'onchange': 'submitFilterForm(this.form);',
            'class': 'mt-3',
        }
        self.code = 'offer_only'
        self.request = request
        self.manager = form.manager
        self.form = form
        self.choices = None

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
        return result_for_other.filter(
            rangeproduct__in=self.get_range_products()
        ).exists()

    def get_range_products(self):
        """
        :returns: All range products for the request user.
        """
        if hasattr(RangeProduct, 'for_user'):
            return RangeProduct.for_user(self.request.user)  # @UndefinedVariable
        return RangeProduct.active_special_prices.all()

    @property
    def query(self):
        """
        :returns: Query to filter the result containing only offers for this
        user when the Checkbox is checked.
        """
        if self.request.GET.get('offer_only', False) == 'on':
            return Q(rangeproduct__in=self.get_range_products())
        return None


class ProductFilter(forms.Form):
    """
    This filter has three kinds of fields:
    - MultipleChoiceAttributeField for dynamic attribute value fields
    - MultipleChoiceProductField for product attached data (weight, volume)
    - BooleanOfferField for filtering offers only
    """
    name = 'Filter'
    code = 'filter'
    product_field_codes = (
        ('volume', '{}l'),
        ('weight', '{}kg'),
    )

    def __init__(self, request, manager, qs, *args, **kwargs):
        self.manager = manager
        self.request = request
        self.qs = qs
        super().__init__(request.GET, *args, **kwargs)
        self.fields = self.get_fields()

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

    def get_product_fields(self):
        """
        :returns: Newly created MultipleChoiceProductField's (volume, weight)
        """
        fields = {}

        def _volume_str(value):
            return f'{value}l'

        fields['volume'] = MultipleChoiceProductField(
            'volume', self.request, self, _volume_str, label='Volumen')

        def _weight_str(value):
            return '{}{}'.format(
                (value * 1000).quantize(1) if value < 1 else value,
                'g' if value < 1 else 'kg',)

        fields['weight'] = MultipleChoiceProductField(
            'weight', self.request, self, _weight_str, label='Gewicht')

        return fields

    def get_offer_field(self):
        """
        :returns: BooleanOfferField for offer_only filter
        """
        field = BooleanOfferField(self.request, self)
        if field.get_range_products().exists():
            return {'offer_only': field}
        return {}

    def get_attribute_fields(self):
        """
        :returns: MultipleChoiceAttributeField for dynamic attribute values
        """
        fields = {}
        all_attributes_from_qs = ProductAttribute.objects.filter(
            productattributevalue__product__in=self.qs
        ).order_by(
            'name', 'option_group_id'
        ).distinct(
            'name', 'option_group_id'
        )
        for attribute in all_attributes_from_qs:
            field = MultipleChoiceAttributeField(attribute, self.request, self)
            fields[str(attribute.id)] = field
        return fields

    def get_fields(self):
        """
        :returns: Resorted fields containing the new created.
        """
        fields = {
            **self.get_offer_field(),
            **self.get_product_fields(),
            **self.fields,
            **self.get_attribute_fields(),
        }
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


class UserFilter(forms.Form):
    """
    This filter needs the user to be authenticated.
    It manages two fields with a very similar logic:
    - wishlist
    - order
    """
    name = 'Mein Shop'
    code = 'user'

    wishlist = forms.MultipleChoiceField(
        label='Favoritenlisten',
        widget=forms.SelectMultiple(attrs={'class': 'chosen-select'}),
        required=False,
    )

    order = forms.MultipleChoiceField(
        label='Vorherige Bestellungen',
        widget=forms.SelectMultiple(attrs={'class': 'chosen-select'}),
        required=False,
    )

    def __init__(self, request, manager, qs, *args, **kwargs):
        self.manager = manager
        self.request = request
        self.qs = qs
        super().__init__(request.GET, *args, **kwargs)

    def initialize(self):
        """
        Initializes all fields after the first result was calculated.
        It is executed by the FilterManager from outside.
        This filter needs the user to be authenticated.
        """
        if not self.request.user.is_authenticated:
            self.fields = {}
            return None

        self.fields['wishlist'].choices = self.get_wishlist_choices()
        self.fields['order'].choices = self.get_order_choices()
        result = self.is_valid()
        self._errors = {}
        return result

    def get_wishlist_choices(self):
        """
        :returns: All wishlists of request user as choices.
        """
        return self.request.user.wishlists.values_list('id', 'name')

    def get_order_choices(self):
        """
        :returns: All orders of request user as choices.
        """
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

        if 'wishlist' in self.request.GET:
            wishlist_ids = self.request.GET.getlist('wishlist')
            query |= Q(wishlists_lines__wishlist_id__in=wishlist_ids)

        if 'order' in self.request.GET:
            order_ids = self.request.GET.getlist('order')
            query |= Q(line__order_id__in=order_ids)

        return [query]


FILTERS = [UserFilter, ProductFilter]
            