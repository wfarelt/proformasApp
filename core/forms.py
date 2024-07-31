
from django import forms
from .models import Producto, Cliente, Proforma, Supplier, Brand

# CREAR UN FORMULARIO PARA PRODUCTO
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'brand', 'stock', 'precio', 'location']
        labels = {
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'brand': 'Marca',
            'stock': 'Stock',
            'precio': 'Precio',
            'location': 'Ubicación',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}), # 'type': 'text
            'stock': forms.NumberInput(attrs={'class': 'form-control'}), # 'type': 'number
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),            
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super(ProductoForm, self).__init__(*args, **kwargs)
        self.fields['brand'].queryset = Brand.objects.filter(status=True)

# CREAR UN FORMULARIO PARA CLIENTE
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['name', 'nit', 'email', 'phone', 'address']
        labels = {
            'name': 'Nombre',
            'nit': 'NIT',
            'email': 'Correo',
            'phone': 'Teléfono',
            'address': 'Dirección',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control','autofocus': 'autofocus'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

# CREAR UN FORMULARIO PARA MODIFICAR CLIENTE DE PROFORMA
class ProformaAddClientForm(forms.ModelForm):
    class Meta:
        model = Proforma
        fields = ['cliente']
        labels = {
            'cliente': 'Cliente',
        }
        widgets = {
            'cliente': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
# FORMULARIO PROVEEDOR
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address']
        labels = {
            'name': 'Nombre',
            'contact_person': 'Contacto',
            'phone': 'Teléfono',
            'email': 'Correo',
            'address': 'Dirección',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
# FORMULARIO MARCA
class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'initials','description', 'status']
        labels = {
            'name': 'Nombre',
            'initials': 'Iniciales',
            'description': 'Descripción',
            'status': 'Estado',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'initials': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

