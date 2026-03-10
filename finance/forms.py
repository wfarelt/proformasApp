from django import forms
from django.db.models import Q

from core.models import Proforma
from .models import CashRegister, Payment, Expense


class CashRegisterOpenForm(forms.ModelForm):
    class Meta:
        model = CashRegister
        fields = ['opening_balance', 'notes']
        widgets = {
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'opening_balance': 'Saldo inicial',
            'notes': 'Observación',
        }


class CashRegisterCloseForm(forms.ModelForm):
    class Meta:
        model = CashRegister
        fields = ['closing_balance', 'notes']
        widgets = {
            'closing_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'closing_balance': 'Saldo de cierre',
            'notes': 'Observación',
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['proforma', 'amount', 'method', 'reference', 'notes']
        widgets = {
            'proforma': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'method': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'proforma': 'Proforma',
            'amount': 'Monto',
            'method': 'Método de pago',
            'reference': 'Referencia',
            'notes': 'Observación',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        queryset = Proforma.objects.exclude(estado='ANULADO').select_related('cliente').order_by('-id')

        if user:
            if user.company:
                queryset = queryset.filter(
                    Q(company=user.company) |
                    Q(company__isnull=True, usuario=user)
                )
            else:
                queryset = queryset.filter(usuario=user)

        self.fields['proforma'].queryset = queryset
        self.fields['proforma'].empty_label = 'Seleccione una proforma'
        self.fields['proforma'].label_from_instance = (
            lambda obj: f"#{obj.id} - {obj.proforma__cliente__name()} - {obj.estado} - Total {obj.total}"
        )


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['concept', 'description', 'amount']
        widgets = {
            'concept': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }
        labels = {
            'concept': 'Concepto',
            'description': 'Descripción',
            'amount': 'Monto',
        }
