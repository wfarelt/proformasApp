from django import forms
from decimal import Decimal
from django.db.models import (
    Q,
    F,
    Sum,
    Value,
    OuterRef,
    Subquery,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce

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
    submit_token = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Payment
        fields = ['proforma', 'amount', 'method', 'cash_amount', 'bank_amount', 'reference', 'notes']
        widgets = {
            'proforma': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'method': forms.Select(attrs={'class': 'form-control'}),
            'cash_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'bank_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'proforma': 'Proforma',
            'amount': 'Monto',
            'method': 'Método de pago',
            'cash_amount': 'Monto efectivo',
            'bank_amount': 'Monto banco/transferencia',
            'reference': 'Referencia',
            'notes': 'Observación',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        payment_totals = Payment.objects.filter(
            proforma=OuterRef('pk'),
            status='POSTED',
        ).values('proforma').annotate(
            total=Coalesce(
                Sum('amount'),
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            )
        ).values('total')

        queryset = Proforma.objects.filter(estado='EJECUTADO').annotate(
            total_net_annotated=ExpressionWrapper(
                F('total') - (F('total') * F('discount_percentage') / Value(100)),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            total_paid_annotated=Coalesce(
                Subquery(payment_totals, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
        ).filter(
            total_paid_annotated__lt=F('total_net_annotated')
        ).select_related('cliente').order_by('-id')

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
        self.fields['cash_amount'].required = False
        self.fields['bank_amount'].required = False
        self.fields['proforma'].label_from_instance = (
            lambda obj: (
                f"#{obj.id} - {obj.proforma__cliente__name()} - Total neto {obj.total_net_annotated:.2f} "
                f"- Saldo {(obj.total_net_annotated - obj.total_paid_annotated):.2f}"
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        proforma = cleaned_data.get('proforma')
        amount = cleaned_data.get('amount')
        method = cleaned_data.get('method')
        cash_amount = cleaned_data.get('cash_amount') or Decimal('0.00')
        bank_amount = cleaned_data.get('bank_amount') or Decimal('0.00')

        if not proforma or amount is None:
            return cleaned_data

        if amount <= 0:
            self.add_error('amount', 'El monto debe ser mayor a cero.')
            return cleaned_data

        if method == 'CASH':
            cleaned_data['cash_amount'] = amount
            cleaned_data['bank_amount'] = Decimal('0.00')
        elif method in {'TRANSFER', 'CARD', 'OTHER'}:
            cleaned_data['cash_amount'] = Decimal('0.00')
            cleaned_data['bank_amount'] = amount
        elif method == 'MIXED':
            if cash_amount <= 0 or bank_amount <= 0:
                self.add_error('cash_amount', 'En pago mixto debes ingresar montos mayores a cero.')
                return cleaned_data
            if cash_amount + bank_amount != amount:
                self.add_error('bank_amount', 'En pago mixto, efectivo + banco debe ser igual al monto total.')
                return cleaned_data
            cleaned_data['cash_amount'] = cash_amount
            cleaned_data['bank_amount'] = bank_amount

        if proforma.estado != 'EJECUTADO':
            self.add_error('proforma', 'Solo puedes registrar pagos para proformas ejecutadas.')
            return cleaned_data

        saldo_pendiente = proforma.saldo_pendiente()
        if saldo_pendiente <= 0:
            self.add_error('proforma', 'La proforma seleccionada ya se encuentra pagada.')
            return cleaned_data

        if amount > saldo_pendiente:
            self.add_error(
                'amount',
                f'El monto excede el saldo pendiente ({saldo_pendiente}).'
            )

        return cleaned_data


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
