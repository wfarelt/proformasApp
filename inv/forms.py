from django import forms
from django.forms import inlineformset_factory
from .models import ProductEntry, ProductEntryDetail, Purchase, PurchaseDetail

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

# COMPRAS

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number', 'total_amount', 'status']
        
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class PurchaseDetailForm(forms.ModelForm):
    class Meta:
        model = PurchaseDetail
        fields = ['product', 'quantity', 'unit_price']
        
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control select2'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

PurchaseDetailFormSet = inlineformset_factory(
    Purchase,
    PurchaseDetail,
    form=PurchaseDetailForm,
    fields=('product', 'quantity', 'unit_price'),
    extra=1,
    can_delete=True
)