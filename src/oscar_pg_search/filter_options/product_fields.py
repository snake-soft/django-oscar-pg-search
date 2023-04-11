from decimal import Decimal as D
from django import forms
from django.db.models import Q
from oscar.core.loading import get_model
from .base_fields import ProductFieldBase


RangeProduct = get_model('offer', 'RangeProduct')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


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
