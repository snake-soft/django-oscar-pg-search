from django import forms


class FilterFormBase(forms.Form):
    def __init__(self, request_data, manager, qs, request=None):
        self.request_data = request_data
        self.manager = manager
        self.request = request
        self.wishlist_as_link = manager.wishlist_as_link
        self.qs = qs
        super().__init__(request_data)
        self.fields = self.get_fields()
