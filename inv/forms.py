from django import forms
from django.forms import inlineformset_factory
from .models import Purchase, PurchaseDetail, Producto as Product, Movement, MovementItem

# COMPRAS

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number', 'date', 'total_amount', 'status']
        
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de factura'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),            
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        
        # Cambiar nombre a los labels
        labels = {
            'supplier': 'Proveedor',
            'invoice_number': 'Número de factura',
            'date': 'Fecha',
            'total_amount': 'Monto total',
            'status': 'Estado',
        }

class PurchaseDetailForm(forms.ModelForm):
    class Meta:
        model = PurchaseDetail
        fields = ['product', 'quantity', 'unit_price']
        
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control select2'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Precio unitario'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay instancia existente, usa su producto
        if self.instance.pk and self.instance.product:
            self.fields['product'].queryset = Product.objects.filter(pk=self.instance.product.pk)
        
        else:
            # Si no hay instancia, muestra todos los productos
            self.fields['product'].queryset = Product.objects.all()
            
PurchaseDetailFormSet = inlineformset_factory(
    Purchase,
    PurchaseDetail,
    form=PurchaseDetailForm,
    fields=('product', 'quantity', 'unit_price'),
    extra=1,
    can_delete=True
)

# MOVIMIENTOS

class MovementForm(forms.ModelForm):
    class Meta:
        model = Movement
        fields = ['movement_type', 'description']
        
        widgets = {
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción'}),
            
        }
        
        labels = {
            'movement_type': 'Tipo de movimiento',
            'description': 'Descripción',
            
        }

class MovementItemForm(forms.ModelForm):
    class Meta:
        model = MovementItem
        fields = ['product', 'quantity']
        
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control select2'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
            
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay instancia existente, usa su producto
        if self.instance.pk and self.instance.product:
            self.fields['product'].queryset = Product.objects.filter(pk=self.instance.product.pk)
        
        else:
            # Si no hay instancia, muestra todos los productos
            self.fields['product'].queryset = Product.objects.all()


MovementItemFormSet = inlineformset_factory(
    Movement,
    MovementItem,
    form=MovementItemForm,
    fields=('product', 'quantity'),
    extra=1,
    can_delete=True
)
