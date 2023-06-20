from django.db.models import Q
from oscar.core.loading import get_model
from .base_fields import AttributeFieldBase


RangeProduct = get_model('offer', 'RangeProduct')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


class TextAttributeField(AttributeFieldBase):
    def get_query(self):
        if str(self.attribute.id) in self.request_data:
            values_list = self.request_data.getlist(str(self.attribute.id))
            text_fields = (self.attribute.TEXT, self.attribute.FLOAT,
                           self.attribute.INTEGER)
            if self.attribute.type in text_fields:
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
