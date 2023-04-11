from django import forms
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
