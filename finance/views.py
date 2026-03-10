from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CashRegisterOpenForm, CashRegisterCloseForm, ExpenseForm, PaymentForm
from .models import CashRegister, Expense, Payment, Transaction


@login_required(login_url='login')
def finance_dashboard(request):
    company = request.user.company
    if not company:
        messages.error(request, 'Debes tener una empresa asignada para usar el módulo de finanzas.')
        return redirect('home')

    open_cash = CashRegister.objects.filter(company=company, status='OPEN').first()

    payments_total = Payment.objects.filter(company=company, status='POSTED').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    expenses_total = Expense.objects.filter(company=company, status='POSTED').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    context = {
        'title': 'Finanzas',
        'open_cash': open_cash,
        'payments_total': payments_total,
        'expenses_total': expenses_total,
        'net_total': payments_total - expenses_total,
    }
    return render(request, 'finance/dashboard.html', context)


@login_required(login_url='login')
def cash_register_list(request):
    company = request.user.company
    registers = CashRegister.objects.none()
    if company:
        registers = CashRegister.objects.filter(company=company).order_by('-opened_at')

    return render(request, 'finance/cash_register_list.html', {
        'title': 'Cajas diarias',
        'registers': registers,
    })


@login_required(login_url='login')
@transaction.atomic
def cash_register_open(request):
    company = request.user.company
    if not company:
        messages.error(request, 'Debes tener una empresa asignada para abrir caja.')
        return redirect('home')

    if CashRegister.objects.filter(company=company, status='OPEN').exists():
        messages.warning(request, 'Ya existe una caja abierta para tu empresa.')
        return redirect('cash_register_list')

    form = CashRegisterOpenForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cash_register = form.save(commit=False)
        cash_register.company = company
        cash_register.opened_by = request.user
        cash_register.status = 'OPEN'
        cash_register.opened_at = timezone.now()
        cash_register.save()
        messages.success(request, f'Caja #{cash_register.id} abierta correctamente.')
        return redirect('cash_register_list')

    return render(request, 'finance/cash_register_form.html', {
        'title': 'Abrir caja',
        'form': form,
        'is_closing': False,
    })


@login_required(login_url='login')
@transaction.atomic
def cash_register_close(request, pk):
    cash_register = get_object_or_404(CashRegister, pk=pk, company=request.user.company)
    if cash_register.status == 'CLOSED':
        messages.info(request, 'La caja ya está cerrada.')
        return redirect('cash_register_list')

    form = CashRegisterCloseForm(request.POST or None, instance=cash_register)
    if request.method == 'POST' and form.is_valid():
        closed_register = form.save(commit=False)
        closed_register.status = 'CLOSED'
        closed_register.closed_by = request.user
        closed_register.closed_at = timezone.now()
        closed_register.save()
        messages.success(request, f'Caja #{closed_register.id} cerrada correctamente.')
        return redirect('cash_register_list')

    return render(request, 'finance/cash_register_form.html', {
        'title': f'Cierre de caja #{cash_register.id}',
        'form': form,
        'cash_register': cash_register,
        'is_closing': True,
    })


@login_required(login_url='login')
def transaction_list(request):
    company = request.user.company
    txs = Transaction.objects.none()
    if company:
        txs = Transaction.objects.filter(company=company).select_related('cash_register', 'created_by')

    return render(request, 'finance/transaction_list.html', {
        'title': 'Transacciones',
        'transactions': txs,
    })


@login_required(login_url='login')
@transaction.atomic
def payment_create(request):
    company = request.user.company
    if not company:
        messages.error(request, 'Debes tener una empresa asignada para registrar pagos.')
        return redirect('home')

    form = PaymentForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        payment = form.save(commit=False)
        payment.company = company
        payment.created_by = request.user
        payment.cash_register = CashRegister.objects.filter(company=company, status='OPEN').first()
        payment.save()
        payment_ct = ContentType.objects.get_for_model(Payment)

        Transaction.objects.create(
            company=company,
            cash_register=payment.cash_register,
            transaction_type='IN',
            source='PAYMENT',
            amount=payment.amount,
            description=f'Pago proforma #{payment.proforma.id}',
            occurred_at=payment.paid_at,
            content_type=payment_ct,
            created_by=request.user,
            object_id=payment.id,
        )

        messages.success(request, 'Pago registrado correctamente.')
        return redirect('payment_list')

    return render(request, 'finance/payment_form.html', {
        'title': 'Registrar pago',
        'form': form,
    })


@login_required(login_url='login')
def payment_list(request):
    company = request.user.company
    payments = Payment.objects.none()
    if company:
        payments = Payment.objects.filter(company=company).select_related('proforma', 'cash_register').order_by('-paid_at')

    return render(request, 'finance/payment_list.html', {
        'title': 'Pagos',
        'payments': payments,
    })


@login_required(login_url='login')
@transaction.atomic
def expense_create(request):
    company = request.user.company
    if not company:
        messages.error(request, 'Debes tener una empresa asignada para registrar gastos.')
        return redirect('home')

    form = ExpenseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        expense = form.save(commit=False)
        expense.company = company
        expense.created_by = request.user
        expense.cash_register = CashRegister.objects.filter(company=company, status='OPEN').first()
        expense.save()
        expense_ct = ContentType.objects.get_for_model(Expense)

        Transaction.objects.create(
            company=company,
            cash_register=expense.cash_register,
            transaction_type='OUT',
            source='EXPENSE',
            amount=expense.amount,
            description=f'Gasto: {expense.concept}',
            occurred_at=expense.spent_at,
            content_type=expense_ct,
            created_by=request.user,
            object_id=expense.id,
        )

        messages.success(request, 'Gasto registrado correctamente.')
        return redirect('expense_list')

    return render(request, 'finance/expense_form.html', {
        'title': 'Registrar gasto',
        'form': form,
    })


@login_required(login_url='login')
def expense_list(request):
    company = request.user.company
    expenses = Expense.objects.none()
    if company:
        expenses = Expense.objects.filter(company=company).select_related('cash_register').order_by('-spent_at')

    return render(request, 'finance/expense_list.html', {
        'title': 'Gastos',
        'expenses': expenses,
    })


@login_required(login_url='login')
def finance_reports(request):
    company = request.user.company
    if not company:
        messages.error(request, 'Debes tener una empresa asignada para ver reportes.')
        return redirect('home')

    tx_qs = Transaction.objects.filter(company=company)
    income_total = tx_qs.filter(transaction_type='IN').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']
    expense_total = tx_qs.filter(transaction_type='OUT').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    context = {
        'title': 'Reportes financieros',
        'income_total': income_total,
        'expense_total': expense_total,
        'balance': income_total - expense_total,
        'recent_transactions': tx_qs.select_related('cash_register').order_by('-occurred_at')[:20],
    }
    return render(request, 'finance/reports.html', context)
