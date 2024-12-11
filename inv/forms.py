from django import forms
from django.forms import inlineformset_factory
from .models import Movement, MovementDetail

class MovementForm(forms.ModelForm):
    class Meta:
        model = Movement
        fields = ['movement_type', 'date', 'description', 'supplier', 'total_quantity']
  
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