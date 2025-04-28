
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Producto, Cliente, Proforma, Supplier, Brand, User


# CREAR UN FORMULARIO PARA USUARIO
class UserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'is_staff', 'is_superuser']
        labels = {
            'email': 'Correo',
            'name': 'Nombre',
            'is_staff': 'Staff',
            'is_superuser': 'Superusuario',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# CREAR UN FORMULARIO PARA MODIFICAR USUARIO
class UserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'is_staff', 'is_superuser']
        labels = {
            'email': 'Correo',
            'name': 'Nombre',
            'is_staff': 'Staff',
            'is_superuser': 'Superusuario',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# PASSWORD CHANGE FORM
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label=_("Contraseña actual"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña actual'
        }),
    )
    new_password1 = forms.CharField(
        label=_("Nueva contraseña"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la nueva contraseña'
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("Confirme la nueva contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la nueva contraseña'
        }),
    )

# CREAR UN FORMULARIO PARA PRODUCTO
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'brand', 'stock', 'cost', 'precio', 'location']
        labels = {
            'nombre': 'Código',
            'descripcion': 'Descripción',
            'brand': 'Marca',
            'cost': 'Costo',
            'stock': 'Stock',
            'precio': 'Precio Venta',
            'location': 'Ubicación',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'brand': forms.Select(attrs={'class': 'form-control'}), # 'type': 'text
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}), # 'type': 'number
            'cost': forms.NumberInput(attrs={'class': 'form-control'}), # 'type': 'number
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
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

