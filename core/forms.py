from django import forms

import barcode

from core import models


class BarcodeForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()

        Barcode = barcode.get_barcode_class(self.cleaned_data["type"])
        try:
            Barcode(cleaned_data["barcode"])
        except barcode.errors.BarcodeError as e:
            raise forms.ValidationError(str(e))

        return cleaned_data

    class Meta:
        model = models.Barcode
        exclude = ()
