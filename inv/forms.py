from django import forms
from django.forms import inlineformset_factory
from .models import Movement, MovementDetail

class MovementForm(forms.ModelForm):
    class Meta:
        model = Movement
        fields = ['movement_type', 'date', 'description', 'supplier', 'total_quantity']
    
    def __init__(self, *args, **kwargs):
        super(MovementForm, self).__init__(*args, **kwargs)
        self.fields['movement_type'].widget.attrs.update({'class': 'form-control'})
        self.fields['date'].widget.attrs.update({'class': 'form-control', 'type': 'date'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['supplier'].widget.attrs.update({'class': 'form-control'})
        self.fields['total_quantity'].widget.attrs.update({'class': 'form-control', 'readonly': 'readonly'})
  
# Crear un formulario para MovementDetail
class MovementDetailForm(forms.ModelForm):
    class Meta:
        model = MovementDetail
        fields = ['product', 'quantity', 'cost', 'subtotal']

# Crear un InlineFormSet para MovementDetail
MovementDetailFormSet = inlineformset_factory(
    parent_model=Movement,
    model=MovementDetail,
    form=MovementDetailForm,
    extra=1,  # Número de formularios adicionales que se mostrarán
    can_delete=True  # Permitir eliminar detalles
)