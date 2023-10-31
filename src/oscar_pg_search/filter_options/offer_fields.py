from django import forms
from django.db.models import Q
from oscar.core.loading import get_model


RangeProduct = get_model('offer', 'RangeProduct')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


class BooleanOfferField(forms.BooleanField):
    """
    Field that is only used for the 'Offer only' filter.
    """
    def __init__(self, request_data, form, *args, request=None, **kwargs):
        super().__init__(label='Nur Angebote', required=False, *args, **kwargs)
        self.widget.attrs={
            'onchange': "$('#products').empty();",
            'class': 'mt-3',
        }
        self.code = 'offer_only'
        self.request_data = request_data
        self.manager = form.manager
        self.form = form
        self.choices = None
        self.request = self.manager.request

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
