from django import forms
from .models import Movement, MovementDetail, ProductEntry, ProductEntryDetail

class MovementForm(forms.ModelForm):
    class Meta:
        model = Movement
        fields = ['movement_type', 'date', 'description', 'supplier', 'status']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
        }

class MovementDetailForm(forms.ModelForm):
    class Meta:
        model = MovementDetail
        fields = ['product', 'quantity', 'cost']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

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
    
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
