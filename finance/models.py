from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from core.models import Company, Proforma


class CashRegister(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Abierta'),
        ('CLOSED', 'Cerrada'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cash_registers')
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='opened_cash_registers'
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='closed_cash_registers'
    )

    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')

    class Meta:
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
        ordering = ['-opened_at']
        constraints = [
            models.UniqueConstraint(
                fields=['company'],
                condition=models.Q(status='OPEN'),
                name='uniq_open_cash_register_per_company',
            )
        ]

    def __str__(self):
        return f"Caja #{self.id} - {self.company.name} ({self.status})"


class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Efectivo'),
        ('TRANSFER', 'Transferencia'),
        ('CARD', 'Tarjeta'),
        ('MIXED', 'Mixto'),
        ('OTHER', 'Otro'),
    ]

    STATUS_CHOICES = [
        ('POSTED', 'Registrado'),
        ('VOID', 'Anulado'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    proforma = models.ForeignKey(Proforma, on_delete=models.PROTECT, related_name='payments')
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bank_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='CASH')
    paid_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='POSTED')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-paid_at', '-id']

    def __str__(self):
        return f"Pago #{self.id} - Proforma {self.proforma_id}"


class Expense(models.Model):
    STATUS_CHOICES = [
        ('POSTED', 'Registrado'),
        ('VOID', 'Anulado'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='expenses')
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )

    concept = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    spent_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='POSTED')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['-spent_at', '-id']

    def __str__(self):
        return f"Gasto #{self.id} - {self.concept}"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Ingreso'),
        ('OUT', 'Egreso'),
    ]

    SOURCE_CHOICES = [
        ('PAYMENT', 'Pago'),
        ('EXPENSE', 'Gasto'),
        ('MANUAL', 'Manual'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='MANUAL')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    occurred_at = models.DateTimeField(default=timezone.now)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_document = GenericForeignKey('content_type', 'object_id')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_finance_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'
        ordering = ['-occurred_at', '-id']

    def __str__(self):
        return f"{self.get_transaction_type_display()} #{self.id}"
