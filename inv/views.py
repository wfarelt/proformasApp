# Descargar plantilla de inventario inicial
from openpyxl import Workbook

def download_inventory_template(request):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "inventario"
    sheet.append(["product_code", "quantity", "cost", "precio", "location", "descripcion"])
    sheet.append(["1R0750", 1, 10, 16, "a-1", "Filtro de aceite"])
    sheet.append(["2R0800", 2, 20, 30, "b-2"])
    from io import BytesIO
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="plantilla_inventario_inicial.xlsx"'
    return response
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.timezone import now
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import timedelta, time
from django.db.models import Q, F, Value, IntegerField
from datetime import datetime
from django.utils.timezone import make_aware
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from core.models import Detalle, Proforma
from .models import Producto, Purchase, PurchaseDetail, Movement, MovementItem
from .forms import PurchaseForm, PurchaseDetailFormSet, MovementForm, MovementItemFormSet, InventoryUploadForm

from django.db import transaction
from django.contrib.contenttypes.models import ContentType

# InventoryUploadForm
import openpyxl
from django.db.models import Sum, Count

from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from io import BytesIO

from core.services.purchase_price_service import create_price_history_from_purchase
import json


# INGRESOS

@login_required       
def product_search(request):
    query = request.GET.get('q', '')
    products = Producto.objects.filter(
        Q(nombre__icontains=query) | Q(referencia_cruzada__icontains=query)
    )[:10]  # Muestra solo 10 resultados
    data = [{"id": p.id, "name": p.nombre} for p in products]
    return JsonResponse(data, safe=False)

# REPORTES

@login_required
def reporte_analitica_productos(request):
    dias_permitidos = [7, 15, 30, 60]
    tipo_permitidos = {
        'mas_vendidos': 'Productos más vendidos',
        'rotacion_sin_stock': 'Productos con rotación sin stock',
        'menos_vendidos_con_stock': 'Productos menos vendidos con stock',
        'otros': 'Productos sin movimiento con stock',
    }

    try:
        dias = int(request.GET.get('dias', 15))
    except (TypeError, ValueError):
        dias = 15

    if dias not in dias_permitidos:
        dias = 15

    tipo = request.GET.get('tipo', 'mas_vendidos')
    if tipo not in tipo_permitidos:
        tipo = 'mas_vendidos'

    fecha_limite = now() - timedelta(days=dias)

    detalles_base = Detalle.objects.filter(
        proforma__estado='EJECUTADO',
        proforma__fecha__gte=fecha_limite,
    )

    if getattr(request.user, 'company_id', None):
        detalles_base = detalles_base.filter(proforma__company=request.user.company)

    if tipo == 'mas_vendidos':
        resultados = (
            detalles_base
            .values('producto_id')
            .annotate(
                codigo=F('producto__nombre'),
                descripcion=F('producto__descripcion'),
                stock_actual=F('producto__stock'),
                ubicacion=F('producto__location'),
                indicador=Sum('cantidad'),
            )
            .order_by('-indicador', 'codigo')
        )
    elif tipo == 'rotacion_sin_stock':
        resultados = (
            detalles_base
            .filter(producto__stock__lte=0)
            .values('producto_id')
            .annotate(
                codigo=F('producto__nombre'),
                descripcion=F('producto__descripcion'),
                stock_actual=F('producto__stock'),
                ubicacion=F('producto__location'),
                indicador=Sum('cantidad'),
            )
            .order_by('-indicador', 'codigo')
        )
    elif tipo == 'menos_vendidos_con_stock':
        resultados = (
            detalles_base
            .filter(producto__stock__gt=0)
            .values('producto_id')
            .annotate(
                codigo=F('producto__nombre'),
                descripcion=F('producto__descripcion'),
                stock_actual=F('producto__stock'),
                ubicacion=F('producto__location'),
                indicador=Sum('cantidad'),
            )
            .order_by('indicador', 'codigo')
        )
    else:
        productos_con_movimiento = detalles_base.values_list('producto_id', flat=True).distinct()
        resultados = (
            Producto.objects
            .filter(stock__gt=0)
            .exclude(id__in=productos_con_movimiento)
            .annotate(
                producto_id=F('id'),
                codigo=F('nombre'),
                stock_actual=F('stock'),
                ubicacion=F('location'),
                indicador=Value(0, output_field=IntegerField()),
            )
            .values('producto_id', 'codigo', 'descripcion', 'stock_actual', 'ubicacion', 'indicador')
            .order_by('codigo')
        )

    resultados = resultados[:100]
    paginator = Paginator(resultados, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inv/reports/analitica_productos.html', {
        'title': 'Analitica de productos',
        'page_obj': page_obj,
        'dias': dias,
        'tipo': tipo,
        'dias_permitidos': dias_permitidos,
        'tipo_permitidos': tipo_permitidos,
        'tipo_label': tipo_permitidos[tipo],
        'indicador_label': 'Cantidad vendida' if tipo != 'otros' else 'Movimientos en el periodo',
    })

def historial_ventas_producto(request):
    producto_id = request.GET.get("producto_id")
    dias = int(request.GET.get("dias", 30))  # Rango de días (por defecto, 30 días)

    productos = Producto.objects.all()  # Para llenar el select de productos
    ventas = []

    if producto_id:
        fecha_limite = now() - timedelta(days=dias)
        ventas = (
            Detalle.objects
            .filter(producto_id=producto_id, proforma__estado="EJECUTADO", proforma__fecha__gte=fecha_limite)
            .values("proforma__fecha", "proforma__id", "proforma__cliente__name", "cantidad", "precio_venta", "subtotal")
            .order_by("-proforma__fecha")
        )
        producto = Producto.objects.get(id=producto_id)
    else:
        producto = None

    return render(request, "inv/reports/historial_ventas.html", {
        "productos": productos,
        "ventas": ventas,
        "producto": producto,
        "dias": dias,
        "title": "Historial de producto",
    })
    
def buscar_productos(request):
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))

    productos = Producto.objects.filter(
        Q(nombre__icontains=query) | Q(referencia_cruzada__icontains=query)
    ).order_by('nombre')

    paginator = Paginator(productos, 10)  # 10 productos por página
    productos_pagina = paginator.get_page(page)

    data = {
        "results": [{"id": p.id, "nombre": p.nombre, "description": p.descripcion } for p in productos_pagina],
        "has_next": productos_pagina.has_next()
    }
    return JsonResponse(data)

@login_required
def reporte_inventario(request):
    productos = Producto.objects.filter(stock__gt=0).select_related('brand').order_by('location')

    total_cost = sum((p.cost or 0) * p.stock for p in productos)
    total_price = sum((p.precio or 0) * p.stock for p in productos)
    total_productos = productos.count()

    # Resumen por marca
    brand_summary = {}
    for p in productos:
        brand_name = p.brand.name if p.brand else "Sin Marca"
        if brand_name not in brand_summary:
            brand_summary[brand_name] = {"count": 0, "stock": 0, "cost_value": 0, "price_value": 0}
        brand_summary[brand_name]["count"] += 1
        brand_summary[brand_name]["stock"] += p.stock
        brand_summary[brand_name]["cost_value"] += float(p.cost or 0) * p.stock
        brand_summary[brand_name]["price_value"] += float(p.precio or 0) * p.stock
    brand_summary = sorted(brand_summary.items(), key=lambda x: x[1]["stock"], reverse=True)

    # Resumen por ubicación
    location_summary = {}
    for p in productos:
        loc = p.location or "Sin Ubicación"
        if loc not in location_summary:
            location_summary[loc] = {"count": 0, "stock": 0}
        location_summary[loc]["count"] += 1
        location_summary[loc]["stock"] += p.stock
    location_summary = sorted(location_summary.items(), key=lambda x: x[1]["stock"], reverse=True)

    # Exportar a Excel
    if request.GET.get("export") == "excel":
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventario"
        ws.append(["ID", "Nombre", "Referencia Cruzada", "Marca", "Stock", "Ubicación", "Costo", "Precio"])
        for p in productos:
            ws.append([
                p.id,
                p.nombre,
                p.referencia_cruzada or "",
                p.brand.name if p.brand else "",
                p.stock,
                p.location or "",
                float(p.cost or 0),
                float(p.precio or 0),
            ])
        # Fila de totales
        ws.append(["", "TOTALES", "", "", sum(p.stock for p in productos), "",
                   float(total_cost), float(total_price)])

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="reporte_inventario.xlsx"'
        return response

    context = {
        "title": "Reporte de Inventario",
        "total_cost": total_cost,
        "total_price": total_price,
        "total_productos": total_productos,
        "brand_summary": brand_summary,
        "location_summary": location_summary,
    }

    return render(request, "inv/reports/reporte_inventario.html", context)
    
def proforma_report(request):
    proformas = Proforma.objects.none()
    total_general = 0
    print_mode = request.GET.get('print') == '1'

    today = timezone.localdate()
    default_start = today.replace(day=1)

    fecha_inicio = request.GET.get('fecha_inicio') or default_start.strftime('%Y-%m-%d')
    fecha_fin = request.GET.get('fecha_fin') or today.strftime('%Y-%m-%d')

    month_labels = []
    month_amounts = []
    seller_labels = []
    seller_sales = []

    try:
        fi_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        ff_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Formato de fecha invalido. Se aplico el rango por defecto del mes actual.')
        fi_date = default_start
        ff_date = today
        fecha_inicio = fi_date.strftime('%Y-%m-%d')
        fecha_fin = ff_date.strftime('%Y-%m-%d')

    if fi_date < ff_date:
        fi = make_aware(datetime.combine(fi_date, time.min))
        ff = make_aware(datetime.combine(ff_date + timedelta(days=1), time.min))

        base_queryset = Proforma.objects.filter(
            estado='EJECUTADO',
            fecha__gte=fi,
            fecha__lt=ff,
        )

        proformas_queryset = base_queryset.order_by('-fecha')

        # Calcular total general antes de paginar
        total_general = sum(p.total_neto() for p in proformas_queryset)

        if print_mode:
            # En modo impresión se muestra toda la tabla sin paginación.
            proformas = proformas_queryset
        else:
            # Paginación para navegación en pantalla.
            paginator = Paginator(proformas_queryset, 10)  # 10 por página
            page_number = request.GET.get('page')
            proformas = paginator.get_page(page_number)

        daily_amount_map = {}
        seller_totals = {}
        for proforma in base_queryset.select_related('usuario'):
            day_date = timezone.localtime(proforma.fecha).date()
            daily_amount_map[day_date] = daily_amount_map.get(day_date, 0.0) + float(proforma.total_neto())

            seller_name = getattr(proforma.usuario, 'name', None) or getattr(proforma.usuario, 'username', None) or 'Sin vendedor'
            seller_totals[seller_name] = seller_totals.get(seller_name, 0.0) + float(proforma.total_neto())

        current_day = fi_date
        while current_day <= ff_date:
            month_labels.append(current_day.strftime('%d/%m'))
            month_amounts.append(round(daily_amount_map.get(current_day, 0.0), 2))
            current_day += timedelta(days=1)

        seller_labels = list(seller_totals.keys())
        seller_sales = [round(value, 2) for value in seller_totals.values()]
    else:
        messages.error(request, 'La fecha inicio debe ser menor que la fecha fin.')

    context = {
        'proformas': proformas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'print_mode': print_mode,
        'total_general': total_general,
        'title': 'Reporte de Proformas',
        'month_labels_json': json.dumps(month_labels),
        'month_amounts_json': json.dumps(month_amounts),
        'seller_labels_json': json.dumps(seller_labels),
        'seller_sales_json': json.dumps(seller_sales),
    }
    return render(request, 'inv/reports/proforma_report.html', context)

# COMPRAS

@login_required
def purchase_list(request):
    query = request.GET.get('q')
    tipo = request.GET.get('tipo_busqueda', 'id')
    purchases = Purchase.objects.all().order_by('-id', '-date', 'status')
    if query:
        if tipo == 'id':
            purchases = purchases.filter(id__icontains=query)
        elif tipo == 'proveedor':
            purchases = purchases.filter(supplier__name__icontains=query)
        elif tipo == 'factura':
            purchases = purchases.filter(invoice_number__icontains=query)
    paginator = Paginator(purchases, 10)
    page_number = request.GET.get('page')
    purchases = paginator.get_page(page_number)
    context = {
        'purchases': purchases,
        'title': 'Lista de Compras',
        'subtitle': 'Lista de compras registradas',
        'icon': 'fa-shopping-cart',
        'tipo_busqueda': tipo,  # Para mantener el select en el template
        'q': query, # Para mantener el valor de búsqueda en el template
    }
    return render(request, 'inv/purchase/purchase_list.html', context)

@login_required(login_url='login')
def create_purchase(request):
    company = getattr(request.user, 'company', None)
    default_sale_margin_percentage = float(getattr(company, 'default_sale_margin_percentage', 35) or 35)
        
    if request.method == 'POST':
        form = PurchaseForm(request.POST)

        # Primero validar el formulario principal para construir la instancia
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.user = request.user

            # Asociar el formset a la instancia (aunque no esté guardada aún)
            formset = PurchaseDetailFormSet(request.POST, instance=purchase)

            if formset.is_valid():
                with transaction.atomic():
                    # Guardar purchase y detalles
                    purchase.save()
                    formset.instance = purchase
                    formset.save()

                    # Calcular el total de la compra
                    total = 0
                    for f in formset.forms:
                        if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                            qty = f.cleaned_data.get('quantity', 0)
                            price = f.cleaned_data.get('unit_price', 0)
                            total += qty * price

                    purchase.total_amount = total
                    purchase.save()

                    if purchase.status == 'confirmed':
                        create_purchase_movement(purchase)
                        create_price_history_from_purchase(purchase, request.user)
                        messages.success(request, "Compra confirmada correctamente.")
                        return redirect('purchase_list')
                    else:
                        messages.success(request, "Compra registrada correctamente.")
                        return redirect('update_purchase', pk=purchase.pk)
            else:
                # formset inválido: renderizar con errores
                messages.error(request, "Error en los detalles de la compra.")
        else:
            # form inválido: para renderizar la página con los datos POST
            formset = PurchaseDetailFormSet(request.POST)
    else:
        form = PurchaseForm()
        formset = PurchaseDetailFormSet()

    return render(request, 'inv/purchase/create_purchase.html', {
        'form': form,
        'formset': formset,
        'title': 'Registrar Compra',
        'default_sale_margin_percentage': default_sale_margin_percentage,
    })

@login_required(login_url='login')
def update_purchase(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    company = getattr(request.user, 'company', None)
    default_sale_margin_percentage = float(getattr(company, 'default_sale_margin_percentage', 35) or 35)
    
    if purchase.status == 'confirmed':
        messages.warning(request, "Esta compra ya está confirmada y no se puede modificar.")
        return redirect('purchase_list') 
    
    if request.method == 'POST':
        form = PurchaseForm(request.POST, instance=purchase)
        formset = PurchaseDetailFormSet(request.POST, instance=purchase)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.user = request.user
                #purchase.date = now()
                purchase.save()  # Guardar primero para poder asignarlo a los detalles

                total = 0
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        detail = form.save(commit=False)
                        detail.purchase = purchase
                        detail.save()
                        total += detail.quantity * detail.unit_price

                formset.save()  # 🔥 Aquí se eliminan los marcados con DELETE

                purchase.total_amount = total
                purchase.save()
                
                if purchase.status == 'confirmed':
                    # Redirigir a la lista de compras
                    create_purchase_movement(purchase)
                    
                    # Generar historial de precios PENDING
                    create_price_history_from_purchase(purchase, request.user)
                    
                    messages.success(request, "Compra confirmada y actualizada correctamente.")
                    return redirect('purchase_list')  
                else:   
                    # Si no está confirmado, redirigir a la misma página de actualización
                    messages.success(request, "Compra actualizada correctamente.")
                    return redirect('update_purchase', pk=purchase.pk)
        else:
            # Agregar errores del formulario principal
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"{field_label}: {error}")
            
            # Agregar errores del formset
            for i, formset_error in enumerate(formset.errors):
                if formset_error:
                    for field, errors in formset_error.items():
                        for error in errors:
                            messages.error(request, f"Producto {i+1} - {field}: {error}")
            
            # Mensaje genérico al final
            if form.errors or formset.errors:
                messages.error(request, "Por favor, corrija los errores señalados.")
    else:
        form = PurchaseForm(instance=purchase)
        formset = PurchaseDetailFormSet(instance=purchase)

    details_with_subtotals = [
        {'form': form, 'subtotal': form.instance.subtotal() if form.instance.pk else 0}
        for form in formset
    ]

    return render(request, 'inv/purchase/create_purchase.html', {
        'form': form,
        'formset': formset,
        'purchase': purchase,
        'details': details_with_subtotals,
        'title': 'Actualizar Compra',
        'default_sale_margin_percentage': default_sale_margin_percentage,
    })

def revert_purchase_movement(purchase):
    ct = ContentType.objects.get_for_model(purchase)

    # Evita duplicar egresos si la anulación se procesa más de una vez.
    existing_out = Movement.objects.filter(
        content_type=ct,
        object_id=purchase.id,
        movement_type='OUT'
    ).first()
    if existing_out:
        return existing_out

    movement_in = purchase.movement
    if not movement_in:
        return None

    movement_items = list(movement_in.items.select_related('product'))
    insufficient = []
    for item in movement_items:
        current_stock = item.product.stock or 0
        if current_stock < item.quantity:
            insufficient.append(
                f"{item.product.nombre} (stock actual: {current_stock}, requiere: {item.quantity})"
            )

    if insufficient:
        raise ValueError("Stock insuficiente para anular la compra: " + "; ".join(insufficient))

    # Crear movimiento de egreso solo si el stock alcanza para todos los items.
    movement_out = Movement.objects.create(
        movement_type='OUT',
        content_type=ct,
        object_id=purchase.id,
        user=purchase.user,
        description=f"Egreso por anulación de compra #{purchase.id}"
    )
    for item in movement_items:
        MovementItem.objects.create(
            movement=movement_out,
            product=item.product,
            quantity=item.quantity,  # misma cantidad que el ingreso
            unit_price=item.unit_price or item.product.cost  # Usar el costo guardado en el movimiento original
        )
        item.product.stock = (item.product.stock or 0) - item.quantity
        item.product.save(update_fields=['stock'])
    return movement_out

# No se puede eliminar una compra, solo se puede anular
@login_required
def cancelled_purchase(request, pk):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                purchase = Purchase.objects.select_for_update().get(pk=pk)

                if purchase.status == 'cancelled':
                    messages.warning(request, "La compra ya estaba anulada.")
                    return redirect('purchase_list')

                revert_purchase_movement(purchase)
                purchase.status = 'cancelled'
                purchase.save(update_fields=['status'])

            messages.success(request, "Compra anulada y stock revertido correctamente.")
            return redirect('purchase_list')
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('purchase_list')

    purchase = get_object_or_404(Purchase, pk=pk)
    return render(request, 'inv/purchase/cancelled_purchase.html', {
        'purchase': purchase,
    })

@login_required(login_url='login')
def delete_purchase_detail(request, pk):
    purchase_detail = get_object_or_404(PurchaseDetail, pk=pk)
    if request.method == 'POST':
        purchase_detail.delete()
        messages.success(request, "Detalle de compra eliminado correctamente.")
        return redirect('update_purchase', pk=purchase_detail.purchase.pk)  # Cambia por tu URL real
    return render(request, 'inv/purchase/delete_purchase_detail.html', {
        'purchase_detail': purchase_detail,
    })

# View purchase
def purchase_detail(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    details = PurchaseDetail.objects.filter(purchase=purchase)
    print_mode = request.GET.get('print') == '1'
    context = {
        'purchase': purchase,
        'details': details,
        'title': 'Compra',
        'subtitle': 'Detalles de la compra',
        'icon': 'fa-shopping-cart',
        'print_mode': print_mode,
    }
    
    return render(request, 'inv/purchase/purchase.html', context)

def create_purchase_movement(purchase):
    if purchase.status != 'confirmed':
        return None  # Solo crea movimiento si está confirmado

    # Verificar si ya se creó un movimiento para evitar duplicados y enviar mensaje de error
    if hasattr(purchase, 'movement') and purchase.movement:
        return None

    movement = Movement.objects.create(
        movement_type='IN',
        content_type=ContentType.objects.get_for_model(purchase),
        object_id=purchase.id,
        user=purchase.user,
        description=f"Ingreso generado por la compra #{purchase.id}"
    )

    for detail in purchase.details.all():
        MovementItem.objects.create(
            movement=movement,
            product=detail.product,
            quantity=detail.quantity,
            unit_price=detail.unit_price  # Guardar el costo de compra histórico
        )

        # Actualizar stock del producto
        detail.product.stock += detail.quantity
        
        # Actualizar costo de producto
        detail.product.cost = detail.unit_price
        
        # Actualizar precio de venta del producto
        # detail.product.precio = detail.sale_price
        
        detail.product.save()
        
    return movement

# MOVIMIENTOS DE INVENTARIO
@login_required
def movement_list(request):
    product_id = request.GET.get('producto_id')
    movements = Movement.objects.all().prefetch_related('items__product').order_by('-id', '-date')
    selected_producto_nombre = None
    if product_id:
        try:
            movements = movements.filter(items__product_id=product_id).distinct()
            selected_producto = Producto.objects.get(id=product_id)
            selected_producto_nombre = selected_producto.nombre + " - " + selected_producto.descripcion
        except Producto.DoesNotExist:
            messages.error(request, "Producto no encontrado.")
            return redirect('movement_list')
    paginator = Paginator(movements, 10)  # 10 movimientos por página
    page_number = request.GET.get('page')
    movements = paginator.get_page(page_number)
    context = {
        'movements': movements,
        'title': 'Movimientos',
        'subtitle': 'Lista de movimientos',
        'icon': 'fa-exchange-alt',
        'selected_producto': product_id,
        'selected_producto_nombre': selected_producto_nombre,
    }   
    return render(request, 'inv/movement/movement_list.html', context)

def movement_detail(request, pk):
    # Obtener el movimiento usando el ID
    movement = get_object_or_404(Movement, id=pk)

    # Obtener los MovementItems relacionados con el movimiento
    movement_items = movement.items.all()

    # Retornar la plantilla con el movimiento y sus items
    return render(request, 'inv/movement/movement_detail.html', {
        'movement': movement,
        'movement_items': movement_items,
    })
    
@login_required(login_url='login')
def create_movement(request):
    if request.method == 'POST':
        form = MovementForm(request.POST)
        formset = MovementItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                movement = form.save(commit=False)
                movement.user = request.user
                movement.date = now()
                movement.save()

                formset.instance = movement
                items = formset.save(commit=False)

                for item_form in formset:
                    if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                        product = item_form.cleaned_data.get('product')
                        quantity = item_form.cleaned_data.get('quantity')

                        # Calcular unit_price y subtotal
                        unit_price = product.cost
                        subtotal = unit_price * quantity

                        # Stock antes del movimiento
                        previous_stock = product.stock

                        # Actualizar stock del producto
                        if movement.movement_type == 'IN':
                            product.stock += quantity
                        else:
                            product.stock -= quantity
                        product.save()

                        # Completar los datos del MovementItem
                        item = item_form.save(commit=False)
                        item.unit_price = unit_price
                        item.subtotal = subtotal
                        item.stock_after_movement = product.stock
                        item.save()

                # Guardar eliminados (si se usó `can_delete`)
                formset.save_m2m()

                messages.success(request, "Movimiento registrado correctamente.")
                return redirect('movement_list')
        else:
            messages.error(request, "Error al registrar el movimiento.")
    else:
        form = MovementForm()
        formset = MovementItemFormSet(queryset=MovementItem.objects.none())

    return render(request, 'inv/movement/movement_form.html', {
        'form': form,
        'formset': formset,
    })

def get_producto(request, id):
    producto = Producto.objects.get(pk=id)
    return JsonResponse({
        'id': producto.id,
        'nombre': producto.nombre,
        'cost': float(producto.cost)
    })

def movement_pdf(request, pk):
    movement = get_object_or_404(Movement, pk=pk)
    html_string = render_to_string('inv/movement/pdf.html', {
        'movement': movement,
        'items': movement.items.all()
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = BytesIO()
    html.write_pdf(pdf_file)
    pdf_file.seek(0)

    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'filename=movement_{movement.id}.pdf'

    return response


@login_required
def cargar_inventario_inicial(request):
    from core.services.price_evaluation_service import PriceEvaluationService
    company = getattr(request.user, 'company', None)
    if not company or not getattr(company, 'enable_initial_stock_load', False):
        messages.error(request, 'La carga inicial de stock está deshabilitada para tu empresa.')
        return redirect('movement_list')

    if request.method == 'POST':
        form = InventoryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data['archivo']
            nombre_archivo = archivo.name.lower()
            update_descripcion = form.cleaned_data.get('actualizar_descripcion', False)
            update_costo = form.cleaned_data.get('actualizar_costo', False)
            update_precio = form.cleaned_data.get('actualizar_precio', False)
            update_ubicacion = form.cleaned_data.get('actualizar_ubicacion', False)
            errores = []
            items_a_crear = []
            if nombre_archivo.endswith('.xlsx'):
                wb = openpyxl.load_workbook(archivo)
                ws = wb.active
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    product_code = str(row[0]).strip() if row[0] else None
                    quantity = int(row[1]) if row[1] is not None else 0
                    cost = float(row[2]) if len(row) > 2 and row[2] is not None else None
                    precio = float(row[3]) if len(row) > 3 and row[3] is not None else None
                    location = str(row[4]).strip() if len(row) > 4 and row[4] else None
                    descripcion_producto = str(row[5]).strip() if len(row) > 5 and row[5] else None
                    if not product_code or quantity <= 0:
                        errores.append(f"Línea {i}: Código de producto y cantidad son obligatorios.")
                        continue
                    producto = Producto.objects.filter(nombre=product_code).first()
                    if not producto:
                        # Crear producto si no existe
                        producto = Producto.objects.create(
                            nombre=product_code,
                            descripcion=descripcion_producto or "",
                            cost=cost or 0,
                            precio=precio or 0,
                            stock=0,
                            location=location or ""
                        )
                        # Crear historial de precio inicial
                        if precio is not None:
                            PriceEvaluationService.propose_new_price(
                                product=producto,
                                old_price=0,
                                new_price=precio,
                                user=request.user,
                                reason="Carga de inventario inicial",
                                cost_reference=cost,
                                change_type='INICIAL',
                                auto_approve_on_increase=True
                            )
                        items_a_crear.append((producto, quantity, cost, precio, True))
                    else:
                        # Producto ya existe
                        crear_historial = False
                        precio_anterior = float(producto.precio or 0)

                        if update_descripcion and descripcion_producto is not None:
                            producto.descripcion = descripcion_producto

                        if update_costo and cost is not None:
                            producto.cost = cost

                        if update_ubicacion and location:
                            producto.location = location

                        if update_precio and precio is not None:
                            if producto.stock and precio > precio_anterior:
                                producto.precio = precio
                                crear_historial = True
                            elif not producto.stock:
                                producto.precio = precio
                                crear_historial = True

                        items_a_crear.append((producto, quantity, cost, precio, crear_historial))
                # Fin for
            else:
                errores.append("Solo se permiten archivos Excel (.xlsx).")

            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'inv/movement/cargar_inventario.html', {'form': form})

            # Crear movimiento y cargar items
            with transaction.atomic():
                movimiento = Movement.objects.create(
                    movement_type='IN',
                    description=form.cleaned_data.get('descripcion') or 'Inventario inicial',
                    user=request.user
                )
                for producto, quantity, cost, precio, crear_historial in items_a_crear:
                    MovementItem.objects.create(
                        movement=movimiento,
                        product=producto,
                        quantity=int(quantity),
                        unit_price=cost  # Guardar el costo con el que se creó el movimiento
                    )
                    # Actualizar stock
                    producto.stock = (producto.stock or 0) + int(quantity)
                    producto.save()
                    # Crear historial de precio si corresponde
                    if crear_historial and precio is not None:
                        PriceEvaluationService.propose_new_price(
                            product=producto,
                            old_price=precio,
                            new_price=precio,
                            user=request.user,
                            reason="Actualización por inventario inicial",
                            cost_reference=cost,
                            change_type='INICIAL',
                            auto_approve_on_increase=True
                        )
            messages.success(request, "Inventario inicial cargado correctamente.")
            return redirect('movement_list')
    else:
        form = InventoryUploadForm()
    return render(request, 'inv/movement/cargar_inventario.html', {'form': form})

@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')  # ⚠️ solo si no usas CSRF token con JS
class CreateMovementView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)

            with transaction.atomic():
                # Crear movimiento principal
                movement = Movement.objects.create(
                    movement_type=data['movement_type'],
                    description=data.get('description', ''),
                    user=request.user,
                    status='COMPLETED'
                )

                for item in data['items']:
                    producto = Producto.objects.get(id=item['product_id'])
                    cantidad = int(item['quantity'])

                    # Validar stock si es egreso
                    if movement.movement_type == 'OUT' and producto.stock < cantidad:
                        raise ValueError(f"Stock insuficiente para el producto {producto.nombre}")

                    # Crear ítem
                    MovementItem.objects.create(
                        movement=movement,
                        product=producto,
                        quantity=cantidad,
                        unit_price=producto.cost,
                        stock_after_movement=producto.stock + cantidad if movement.movement_type == 'IN' else producto.stock - cantidad,
                        observation=item.get('observation', '')
                    )

                    # Actualizar stock
                    producto.stock += cantidad if movement.movement_type == 'IN' else -cantidad
                    producto.save()
                    
                    
                # Retornar respuesta exitosa y direccionar a la lista de movimientos
            return JsonResponse({'message': 'Movimiento guardado correctamente.', 'movement_id': movement.id, 'redirect_url': reverse('movement_list')}, status=201 )



        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado.'}, status=404)
        except ValueError as ve:
            return JsonResponse({'error': str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'Ocurrió un error inesperado.', 'detalle': str(e)}, status=500)


# PRE-INVENTARIO

@login_required(login_url='login')
def pre_inventario(request):
    ubicacion = request.GET.get('ubicacion', '__all__')
    query = request.GET.get('q', '')
    con_stock = request.GET.get('con_stock') == 'on'
    sin_costo = request.GET.get('sin_costo') == 'on'
    sin_precio = request.GET.get('sin_precio') == 'on'

    productos = Producto.objects.all()

    # Filtro de ubicación
    if ubicacion == "":
        # Solo productos sin ubicación (location vacío o None)
        productos = productos.filter(Q(location__exact="") | Q(location__isnull=True))
    elif ubicacion != "__all__":
        productos = productos.filter(location__iexact=ubicacion)
    # Si es "__all__", no se filtra por ubicación

    # Filtro de búsqueda
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query)
            | Q(referencia_cruzada__icontains=query)
            | Q(descripcion__icontains=query)
        )
    # Filtro de stock
    if con_stock:
        productos = productos.filter(stock__gt=0)

    # Filtro sin costo
    if sin_costo:
        productos = productos.filter(Q(cost__isnull=True) | Q(cost=0))
    
    # Filtro sin precio
    if sin_precio:
        productos = productos.filter(Q(precio__isnull=True) | Q(precio=0))
        
        
    # Lista de ubicaciones distintas (sin None ni vacío)
    ubicaciones = Producto.objects.exclude(location__isnull=True).exclude(location__exact="").values_list('location', flat=True).distinct().order_by('location')

    paginator = Paginator(productos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'productos': page_obj,
        'ubicaciones': ubicaciones,
        'ubicacion_actual': ubicacion,
        'query': query,
        'con_stock': con_stock,
        'sin_costo': sin_costo,
        'sin_precio': sin_precio,
        'title': 'Pre-inventario por ubicación',
        'placeholder': 'Buscar por código, referencia cruzada o descripción'
    }
    return render(request, 'inv/reports/pre_inventario.html', context)