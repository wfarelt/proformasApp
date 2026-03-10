from django.urls import path

from finance.views import (
    finance_dashboard,
    cash_register_list,
    cash_register_open,
    cash_register_close,
    transaction_list,
    payment_list,
    payment_create,
    expense_list,
    expense_create,
    finance_reports,
)

urlpatterns = [
    path('', finance_dashboard, name='finance_dashboard'),

    path('cash-register/', cash_register_list, name='cash_register_list'),
    path('cash-register/open/', cash_register_open, name='cash_register_open'),
    path('cash-register/<int:pk>/close/', cash_register_close, name='cash_register_close'),

    path('transactions/', transaction_list, name='transaction_list'),

    path('payments/', payment_list, name='payment_list'),
    path('payments/new/', payment_create, name='payment_create'),

    path('expenses/', expense_list, name='expense_list'),
    path('expenses/new/', expense_create, name='expense_create'),

    path('reports/', finance_reports, name='finance_reports'),
]
