from django.forms import ModelForm, HiddenInput

from .models import BoundarySource

class BoundarySourceForm(ModelForm):
    class Meta:
        model = BoundarySource
        exclude = []
        widgets = {'type': HiddenInput()}
