from decimal import Decimal
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Sum, Value, DecimalField, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

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
    cash_income_total = Payment.objects.filter(company=company, status='POSTED').aggregate(
        total=Coalesce(Sum('cash_amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']
    bank_income_total = Payment.objects.filter(company=company, status='POSTED').aggregate(
        total=Coalesce(Sum('bank_amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    expenses_total = Expense.objects.filter(company=company, status='POSTED').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    context = {
        'title': 'Finanzas',
        'open_cash': open_cash,
        'payments_total': payments_total,
        'cash_income_total': cash_income_total,
        'bank_income_total': bank_income_total,
        'expenses_total': expenses_total,
        'net_total': payments_total - expenses_total,
    }
    return render(request, 'finance/dashboard.html', context)


@login_required(login_url='login')
def cash_register_list(request):
    company = request.user.company
    registers = CashRegister.objects.none()
    if company:
        registers = CashRegister.objects.filter(company=company).select_related('opened_by', 'closed_by').annotate(
            incomes=Coalesce(
                Sum('payments__cash_amount', filter=Q(payments__status='POSTED')),
                Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
            expenses_total=Coalesce(
                Sum('expenses__amount', filter=Q(expenses__status='POSTED')),
                Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
        ).order_by('-opened_at')

        for register in registers:
            register.expected_balance = register.opening_balance + register.incomes - register.expenses_total

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

    last_closed_register = CashRegister.objects.filter(
        company=company,
        status='CLOSED',
    ).order_by('-closed_at', '-id').first()

    previous_balance = None
    if last_closed_register:
        previous_balance = (
            last_closed_register.closing_balance
            if last_closed_register.closing_balance is not None
            else last_closed_register.opening_balance
        )

    if request.method == 'POST':
        form = CashRegisterOpenForm(request.POST)
    else:
        form = CashRegisterOpenForm(initial={
            'opening_balance': previous_balance if previous_balance is not None else Decimal('0.00')
        })

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
        'previous_balance': previous_balance,
        'last_closed_register': last_closed_register,
    })


@login_required(login_url='login')
@transaction.atomic
def cash_register_close(request, pk):
    cash_register = get_object_or_404(CashRegister, pk=pk, company=request.user.company)
    if cash_register.status == 'CLOSED':
        messages.info(request, 'La caja ya está cerrada.')
        return redirect('cash_register_list')

    incomes = cash_register.payments.filter(status='POSTED').aggregate(
        total=Coalesce(
            Sum('cash_amount'),
            Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total']
    expenses_total = cash_register.expenses.filter(status='POSTED').aggregate(
        total=Coalesce(
            Sum('amount'),
            Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total']
    expected_balance = cash_register.opening_balance + incomes - expenses_total

    if request.method == 'POST':
        form = CashRegisterCloseForm(request.POST, instance=cash_register)
    else:
        initial = {}
        if cash_register.closing_balance is None:
            initial['closing_balance'] = expected_balance
        form = CashRegisterCloseForm(instance=cash_register, initial=initial)

    if request.method == 'POST' and form.is_valid():
        closed_register = form.save(commit=False)
        closed_register.status = 'CLOSED'
        closed_register.closed_by = request.user
        closed_register.closed_at = timezone.now()
        closed_register.save()

        difference = closed_register.closing_balance - expected_balance
        if difference == Decimal('0.00'):
            messages.success(request, f'Caja #{closed_register.id} cerrada correctamente. Caja cuadrada.')
        else:
            messages.warning(
                request,
                f'Caja #{closed_register.id} cerrada con diferencia de {difference:.2f}.'
            )
        return redirect('cash_register_list')

    return render(request, 'finance/cash_register_form.html', {
        'title': f'Cierre de caja #{cash_register.id}',
        'form': form,
        'cash_register': cash_register,
        'is_closing': True,
        'expected_balance': expected_balance,
        'incomes': incomes,
        'expenses_total': expenses_total,
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

    open_cash_register = CashRegister.objects.filter(company=company, status='OPEN').first()

    if request.method == 'POST':
        form = PaymentForm(request.POST, user=request.user)
        posted_token = request.POST.get('submit_token')
        expected_token = request.session.get('payment_submit_token')

        if not posted_token or posted_token != expected_token:
            messages.warning(request, 'Este formulario ya fue procesado o expiró. Intenta nuevamente.')
            return redirect('payment_create')

        if form.is_valid():
            # Invalida el token antes de guardar para evitar doble envio por refresh/doble click.
            request.session.pop('payment_submit_token', None)

            payment = form.save(commit=False)
            payment.company = company
            payment.created_by = request.user
            payment.cash_amount = form.cleaned_data.get('cash_amount', Decimal('0.00'))
            payment.bank_amount = form.cleaned_data.get('bank_amount', Decimal('0.00'))

            if payment.cash_amount > 0 and not open_cash_register:
                messages.error(request, 'Debes abrir una caja para registrar montos en efectivo.')
                return redirect('cash_register_open')

            payment.cash_register = open_cash_register if payment.cash_amount > 0 else None

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
    else:
        form = PaymentForm(user=request.user)

    if not request.session.get('payment_submit_token'):
        request.session['payment_submit_token'] = uuid4().hex

    form.fields['submit_token'].initial = request.session['payment_submit_token']

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
        for payment in payments:
            payment.proforma_total_neto = payment.proforma.total_neto()
            payment.proforma_saldo_pendiente = payment.proforma.saldo_pendiente()

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

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    date_from = parse_date(date_from_str) if date_from_str else None
    date_to = parse_date(date_to_str) if date_to_str else None

    tx_qs = Transaction.objects.filter(company=company)
    payment_qs = Payment.objects.filter(company=company, status='POSTED')
    expense_qs = Expense.objects.filter(company=company, status='POSTED')

    if date_from:
        tx_qs = tx_qs.filter(occurred_at__date__gte=date_from)
        payment_qs = payment_qs.filter(paid_at__date__gte=date_from)
        expense_qs = expense_qs.filter(spent_at__date__gte=date_from)
    if date_to:
        tx_qs = tx_qs.filter(occurred_at__date__lte=date_to)
        payment_qs = payment_qs.filter(paid_at__date__lte=date_to)
        expense_qs = expense_qs.filter(spent_at__date__lte=date_to)

    income_total = tx_qs.filter(transaction_type='IN').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']
    expense_total = tx_qs.filter(transaction_type='OUT').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    cash_income = payment_qs.aggregate(
        total=Coalesce(Sum('cash_amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']
    bank_income = payment_qs.aggregate(
        total=Coalesce(Sum('bank_amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']
    total_expenses = expense_qs.aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total']

    cash_net = cash_income - total_expenses
    bank_net = bank_income

    context = {
        'title': 'Reportes financieros',
        'date_from': date_from_str,
        'date_to': date_to_str,
        'income_total': income_total,
        'expense_total': expense_total,
        'balance': income_total - expense_total,
        'cash_income': cash_income,
        'bank_income': bank_income,
        'total_expenses': total_expenses,
        'cash_net': cash_net,
        'bank_net': bank_net,
        'recent_transactions': tx_qs.select_related('cash_register').order_by('-occurred_at')[:20],
    }
    return render(request, 'finance/reports.html', context)
