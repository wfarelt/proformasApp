
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
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
        fields = ['username', 'email', 'name', 'company', 'is_staff', 'is_superuser']
        labels = {
            'username': 'Usuario',
            'email': 'Correo',
            'name': 'Nombre',
            'company': 'Empresa',
            'is_staff': 'Staff',
            'is_superuser': 'Superusuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# CREAR UN FORMULARIO PARA MODIFICAR USUARIO
class UserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'name', 'company', 'is_staff', 'is_superuser']
        labels = {
            'username': 'Usuario',
            'email': 'Correo',
            'name': 'Nombre',
            'company': 'Empresa',
            'is_staff': 'Staff',
            'is_superuser': 'Superusuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
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

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'name', 'email', 'company', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            'username': 'Usuario',
            'name': 'Nombre completo',
            'email': 'Correo electrónico',
            'company': 'Empresa',
            'profile_picture': 'Foto de perfil',
        }
    
    # Editar ClearableFileInput para los labes Change= Cambiar, Clear= Eliminar, y el checkbox
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['profile_picture'].widget.clear_checkbox_label = 'Eliminar'
        self.fields['profile_picture'].widget.initial_text = 'Foto actual'
        self.fields['profile_picture'].widget.input_text = 'Cambiar'
          
          
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
        self.company = kwargs.pop('company', None)
        super(ProductoForm, self).__init__(*args, **kwargs)
        self.fields['brand'].queryset = Brand.objects.filter(status=True)

        config = self._get_custom_config()
        self.custom_field_names = []
        for key, field_cfg in config.items():
            field_name = f"custom__{key}"
            self.custom_field_names.append(field_name)
            self.fields[field_name] = self._build_dynamic_field(field_cfg)

            initial_value = (self.instance.custom_attributes or {}).get(key) if self.instance and self.instance.pk else None
            if initial_value is not None:
                self.initial[field_name] = initial_value

    def _get_custom_config(self):
        if not self.company:
            return {}
        config = getattr(self.company, 'product_custom_fields_config', {}) or {}
        return config if isinstance(config, dict) else {}

    def _build_dynamic_field(self, field_cfg):
        field_type = field_cfg.get('type', 'text')
        label = field_cfg.get('label', 'Campo Personalizado')
        required = field_cfg.get('required', False)

        common_kwargs = {
            'label': label,
            'required': required,
            'help_text': field_cfg.get('help_text', ''),
        }

        if field_type == 'number':
            min_value = field_cfg.get('min')
            max_value = field_cfg.get('max')
            return forms.DecimalField(
                min_value=Decimal(str(min_value)) if min_value is not None else None,
                max_value=Decimal(str(max_value)) if max_value is not None else None,
                widget=forms.NumberInput(attrs={'class': 'form-control'}),
                **common_kwargs,
            )

        if field_type == 'date':
            return forms.DateField(
                widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                **common_kwargs,
            )

        if field_type == 'boolean':
            return forms.BooleanField(
                required=False,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                label=label,
                help_text=field_cfg.get('help_text', ''),
            )

        if field_type == 'select':
            options = field_cfg.get('options', [])
            choices = [('', '---------')]
            for option in options:
                if isinstance(option, dict):
                    choices.append((option.get('value', ''), option.get('label', option.get('value', ''))))
                else:
                    choices.append((option, option))
            return forms.ChoiceField(
                choices=choices,
                widget=forms.Select(attrs={'class': 'form-control'}),
                **common_kwargs,
            )

        return forms.CharField(
            widget=forms.TextInput(attrs={'class': 'form-control'}),
            **common_kwargs,
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        custom_attributes = dict(instance.custom_attributes or {})

        for field_name in getattr(self, 'custom_field_names', []):
            key = field_name.replace('custom__', '', 1)
            value = self.cleaned_data.get(field_name)
            if value in (None, ''):
                custom_attributes.pop(key, None)
                continue
            if hasattr(value, 'isoformat'):
                custom_attributes[key] = value.isoformat()
            else:
                custom_attributes[key] = str(value) if isinstance(value, Decimal) else value

        instance.custom_attributes = custom_attributes
        if commit:
            instance.save()
        return instance


class ProductCatalogImportForm(forms.Form):
    file = forms.FileField(
        label='Archivo Excel',
        help_text='Formatos permitidos: .xlsx, .xlsm',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        allowed_extensions = ('.xlsx', '.xlsm')
        filename = (uploaded_file.name or '').lower()
        if not filename.endswith(allowed_extensions):
            raise ValidationError('Solo se permiten archivos Excel (.xlsx o .xlsm).')
        return uploaded_file

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
    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('El nombre de la marca es obligatorio.')

        queryset = Brand.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError('Ya existe una marca con ese nombre.')

        return name

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


# FORMULARIOS PARA KITS DE PRODUCTOS

from .models import ProductKit, ProductKitItem, Producto

class ProductKitForm(forms.ModelForm):
    class Meta:
        model = ProductKit
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del kit'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción'}),
        }

class ProductKitItemForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = ProductKitItem
        fields = ['producto', 'cantidad']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }