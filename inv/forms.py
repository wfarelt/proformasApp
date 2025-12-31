from django import forms
from django.forms import inlineformset_factory
from .models import Purchase, PurchaseDetail, Producto as Product, Movement, MovementItem
from core.models import Supplier

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
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optimizar la carga de proveedores con select_related
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        
class PurchaseDetailForm(forms.ModelForm):    
    class Meta:
        model = PurchaseDetail
        fields = ['product', 'quantity', 'unit_price', 'sale_price']
        
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control select2'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity', 'min': '1', 'placeholder': 'Cantidad'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control unit-price', 'step': '0.01', 'placeholder': 'Costo unitario'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control sale-price', 'step': '0.01', 'placeholder': 'Precio de venta'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Evita precargar todos los productos por defecto
        self.fields['product'].queryset = Product.objects.none()

        # Si es una instancia existente, aseguramos que su producto esté disponible
        if self.instance and getattr(self.instance, 'pk', None) and getattr(self.instance, 'product', None):
            self.fields['product'].queryset = Product.objects.filter(pk=self.instance.product.pk)
            return

        # Si el formulario viene ligado (POST), intentar extraer el valor enviado para aceptar la validación
        if self.is_bound:
            product_field_name = self.add_prefix('product')

            # Intentar obtener el valor enviado por varias vías
            product_val = self.data.get(product_field_name) or self.data.get('product') or self.data.get(self.add_prefix('product'))

            if product_val:
                try:
                    # Incluimos explícitamente el producto enviado en el queryset para que la validación lo acepte
                    self.fields['product'].queryset = Product.objects.filter(pk=product_val)
                except (ValueError, TypeError):
                    self.fields['product'].queryset = Product.objects.none()
            else:
                # Sin valor enviado, mantener queryset vacío para evitar cargar todo
                self.fields['product'].queryset = Product.objects.none()
        else:
            # Formularios no ligados: mostrar un subconjunto razonable (por ejemplo, primeros 50)
            self.fields['product'].queryset = Product.objects.all()[:50]
               
PurchaseDetailFormSet = inlineformset_factory(
    Purchase,
    PurchaseDetail,
    form=PurchaseDetailForm,
    fields=('product', 'quantity', 'unit_price', 'sale_price'),
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
            'product': forms.Select(attrs={'class': 'form-control select2'}),  # ya estás usando select2
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ⚠️ Evita precargar todos los productos
        if self.instance and self.instance.pk:
            self.fields['product'].queryset = Product.objects.filter(pk=self.instance.product.pk)
        else:
            self.fields['product'].queryset = Product.objects.none()


MovementItemFormSet = inlineformset_factory(
    Movement,
    MovementItem,
    form=MovementItemForm,
    fields=('product', 'quantity'),
    extra=1,
)

class InventoryUploadForm(forms.Form):
    archivo = forms.FileField(label='Archivo XLSX')

            
            
            