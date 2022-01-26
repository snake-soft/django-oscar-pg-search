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
from django.conf import settings
from oscar.core.loading import get_model

RangeProduct = get_model('offer', 'RangeProduct')
Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


class FieldBase:
    widget = forms.SelectMultiple(attrs={'class': 'chosen-select'})

    def __init__(self, attribute, request, form, *args, **kwargs):
        super().__init__(label=attribute.name, required=False, *args, **kwargs)
        self.attribute = attribute
        self.fieldname = f'value_{attribute.type}'
        self.request = request
        self.manager = form.manager
        self.form = form

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


class TextAttributeField(FieldBase, forms.MultipleChoiceField):
    def get_query(self):
        if str(self.attribute.id) in self.request.GET:
            values_list = self.request.GET.getlist(str(self.attribute.id))
            if self.attribute.type in (self.attribute.TEXT, self.attribute.FLOAT):
                values = self.attribute.productattributevalue_set.filter(
                    id__in=values_list)
                values = values.values_list(self.fieldname, flat=True)
                query_kwargs = {
                    f'attribute_values__{self.fieldname}__in': values,
                }
                return Q(**query_kwargs)
            '''
            values_list = self.request.GET.getlist(str(self.attribute.id))
            values = self.attribute.productattributevalue_set.filter(id__in=values_list).values_list('value_text', flat=True)
            return Q(attribute_values__value_text__in=values)
            '''
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

        '''
        return ProductAttributeValue.objects.filter(attribute=self.attribute, product__in=other_field_results_qs).order_by('value_text', 'id').distinct('value_text').values_list('id', 'value_text')
        if self.attribute.code=='alkoholgehalt':
            import pdb; pdb.set_trace()  # <---------
        ProductAttributeValue.objects.first()
        return self.attribute.productattributevalue_set.filter(id__in=other_field_results_qs).order_by('value_text', 'id').distinct('value_text').values_list('id', self.fieldname)

        return self.attribute.productattributevalue_set.distinct(self.fieldname).values_list('id', self.fieldname)
        import pdb; pdb.set_trace()  # <---------
        assert 118511 in other_field_results_qs.values_list('id', flat=True)
        return self.attribute.productattributevalue_set.all().distinct(self.fieldname).values_list('id', self.fieldname)
        #if self.attribute.type == self.attribute.TEXT:
        qs = self.attribute.productattributevalue_set.filter(
            product__in=other_field_results_qs)
        #qs = qs.distinct(self.fieldname)
        import pdb; pdb.set_trace()  # <---------
        values = qs.values_list(self.fieldname, flat=True)
        qs = qs.filter(**{f'{self.fieldname}__in': values})
        return qs.values_list('id', self.fieldname)
        '''


class MultipleChoiceAttributeField(FieldBase, forms.MultipleChoiceField):
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
                and self.attribute.code in self.request.GET:
            result = self.request.GET.getlist(self.attribute.code)
        else:
            result = self.request.GET.getlist(str(self.attribute.id))
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


class ProductFieldBase:
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
        return self.get_query()

    def get_query(self):
        return NotImplementedError('Not implemented in subclass')

    def get_choices(self):
        return NotImplementedError('Not implemented in subclass')


class MultipleChoiceProductField(ProductFieldBase, forms.MultipleChoiceField):
    """
    This field is for weight and volume. They are attached directly to the
    Product.
    """
    def get_query(self):
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


class ForeignKeyProductField(ProductFieldBase, forms.MultipleChoiceField):
    widget = forms.SelectMultiple(attrs={'class': 'chosen-select'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_field = Product._meta.get_field(self.code)
        self.related_name = self.model_field.related_query_name()

    def get_query(self):
        option_ids = self.request.GET.getlist(self.code)
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
    enabled_attributes = getattr(settings, 'OSCAR_ENABLED_ATTRIBUTES', None)
    enabled_attached_fields = getattr(
        settings, 'OSCAR_SEARCH_ENABLED_FIELDS', [])
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
            return f'{float(value)}l'

        fields['volume'] = MultipleChoiceProductField(
            'volume', self.request, self, _volume_str)#, label='Volumen')

        def _weight_str(value):
            return '{}{}'.format(
                (value * 1000).quantize(1) if value < 1 else value,
                'g' if value < 1 else 'kg',)

        fields['weight'] = MultipleChoiceProductField(
            'weight', self.request, self, _weight_str)#, label='Gewicht')

        for field_name in self.enabled_attached_fields:
            model_field = Product._meta.get_field(field_name)

            if model_field.get_internal_type() == 'ForeignKey':
                def _fk_str(value):
                    import pdb; pdb.set_trace()  # <---------
    
                label = model_field.related_model._meta.verbose_name
                fields[field_name] = ForeignKeyProductField(
                    field_name, self.request, self, _fk_str)

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
            if self.enabled_attributes \
                    and attribute.code not in self.enabled_attributes:
                continue

            if attribute.type in (attribute.TEXT, attribute.FLOAT):
                field = TextAttributeField(attribute, self.request, self)
            elif attribute.type in (attribute.OPTION, attribute.MULTI_OPTION):
                field = MultipleChoiceAttributeField(
                    attribute, self.request, self)
            else:
                raise NotImplementedError('Other fields need to be created')
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
            