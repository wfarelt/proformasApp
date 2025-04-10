from django import forms
from django.forms import inlineformset_factory
from .models import  ProductEntry, ProductEntryDetail

# INGRESOS

class ProductEntryForm(forms.ModelForm):
    class Meta:
        model = ProductEntry
        fields = ['description', 'status']
    
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class ProductEntryDetailForm(forms.ModelForm):
    class Meta:
        model = ProductEntryDetail
        fields = ['product', 'quantity', 'unit_cost']
        
        # Poner los widgets en una fila para tabla
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control select2'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

ProductEntryDetailFormSet = inlineformset_factory(
    ProductEntry,
    ProductEntryDetail,
    form=ProductEntryDetailForm,
    fields=['product', 'quantity', 'unit_cost'],
    extra=1,
    can_delete=True
)