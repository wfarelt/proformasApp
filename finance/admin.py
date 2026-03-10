from django.contrib import admin

from .models import CashRegister, Transaction, Payment, Expense


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'status', 'opening_balance', 'closing_balance', 'opened_at', 'closed_at')
    list_filter = ('status', 'company')
    search_fields = ('company__name', 'opened_by__username')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'transaction_type', 'source', 'amount', 'occurred_at', 'cash_register')
    list_filter = ('transaction_type', 'source', 'company')
    search_fields = ('description',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'proforma', 'amount', 'method', 'paid_at', 'status')
    list_filter = ('status', 'method', 'company')
    search_fields = ('reference', 'proforma__id')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'concept', 'amount', 'spent_at', 'status')
    list_filter = ('status', 'company')
    search_fields = ('concept', 'description')
