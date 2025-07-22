from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.timezone import now
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from datetime import timedelta
from django.db.models import Q
from datetime import datetime
from django.utils.timezone import make_aware

from core.models import Producto, Detalle, Proforma
from .models import Producto, Purchase, PurchaseDetail, Movement, MovementItem
from .forms import  PurchaseForm, PurchaseDetailFormSet, MovementForm, MovementItemFormSet

from django.db import transaction
from django.contrib.contenttypes.models import ContentType

# InventoryUploadForm
import io
import csv
import openpyxl
from .forms import InventoryUploadForm

from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum

from django.http import JsonResponse

from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from io import BytesIO

# INGRESOS

@login_required       
def product_search(request):
    query = request.GET.get('q', '')
    products = Producto.objects.filter(nombre__icontains=query)[:10]  # Muestra solo 10 resultados
    data = [{"id": p.id, "name": p.nombre} for p in products]
    return JsonResponse(data, safe=False)

# REPORTES

def reporte_productos_mas_vendidos(request):
    dias = request.GET.get("dias", 15)  # Obtener el valor del formulario (15 por defecto)
    
    try:
        dias = int(dias)  # Convertir a entero
    except ValueError:
        dias = 15  # Si hay error, usar 15 días por defecto
    
    productos = productos_mas_vendidos(dias)
    
    return render(request, "inv/reports/productos_mas_vendidos.html", {
        "productos": productos, 
        "dias": dias,
        "title": "Productos más vendidos",
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

    productos = Producto.objects.filter(nombre__icontains=query).order_by('nombre')

    paginator = Paginator(productos, 10)  # 10 productos por página
    productos_pagina = paginator.get_page(page)

    data = {
        "results": [{"id": p.id, "nombre": p.nombre} for p in productos_pagina],
        "has_next": productos_pagina.has_next()
    }
    return JsonResponse(data)

def reporte_inventario(request):
    productos = Producto.objects.filter(stock__gt=0).order_by('location')  # Solo productos con stock > 0
    return render(request, "inv/reports/reporte_inventario.html", {
        "title": "Reporte de Inventario",
        "productos": productos
    })

def proforma_report(request):
    proformas = Proforma.objects.none()
    total_general = 0

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        try:
            fi = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            ff = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d')) + timedelta(days=1)
            proformas_queryset = Proforma.objects.filter(
                estado='EJECUTADO',
                fecha__range=(fi, ff)
            ).order_by('-fecha')

            # Calcular total general antes de paginar
            total_general = sum(p.total_neto() for p in proformas_queryset)

            # Paginación
            paginator = Paginator(proformas_queryset, 10)  # 10 por página
            page_number = request.GET.get('page')
            proformas = paginator.get_page(page_number)

        except ValueError:
            pass

    context = {
        'proformas': proformas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_general': total_general,
        'title': 'Reporte de Proformas',
    }
    return render(request, 'inv/reports/proforma_report.html', context)

def productos_mas_vendidos(dias=15):
    fecha_limite = now() - timedelta(days=dias)  # Calcular la fecha desde donde filtrar
    productos = (
        Detalle.objects
        .filter(proforma__estado="EJECUTADO", proforma__fecha__gte=fecha_limite)  # Filtrar por fecha
        .values("producto__nombre", "producto__descripcion", "producto__stock")
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")
    )
    return productos

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
    paginator = Paginator(purchases, 10)
    page_number = request.GET.get('page')
    purchases = paginator.get_page(page_number)
    context = {
        'purchases': purchases,
        'title': 'Lista de Compras',
        'subtitle': 'Lista de compras registradas',
        'icon': 'fa-shopping-cart',
    }
    return render(request, 'inv/purchase/purchase_list.html', context)

def create_purchase(request):
        
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        formset = PurchaseDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Crear la compra sin guardar aún
                purchase = form.save(commit=False)
                purchase.user = request.user
                #purchase.date = now()
                purchase.save()

                # Guardar detalles de la compra
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

                messages.success(request, "Compra registrada correctamente.")

                # Redireccionar si está confirmada
                if purchase.status == 'confirmed':
                    create_purchase_movement(purchase)
                    messages.success(request, "Compra confirmada correctamente.")
                    return redirect('purchase_list')
                else:
                    return redirect('update_purchase', pk=purchase.pk)
        else:
            messages.error(request, "Error al registrar la compra.")
    else:
        form = PurchaseForm()
        formset = PurchaseDetailFormSet()

    return render(request, 'inv/purchase/create_purchase.html', {
        'form': form,
        'formset': formset,
    })

def update_purchase(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    
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
                    messages.success(request, "Compra confirmada y actualizada correctamente.")
                    return redirect('purchase_list')  
                else:   
                    # Si no está confirmado, redirigir a la misma página de actualización
                    messages.success(request, "Compra actualizada correctamente.")
                    return redirect('update_purchase', pk=purchase.pk)
        else:
            messages.error(request, "Error al actualizar la compra. Por favor, revise los datos.")
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
    })

def revert_purchase_movement(purchase):
    # Solo si la compra tiene un movimiento de ingreso
    if hasattr(purchase, 'movement'):
        movement_in = purchase.movement
        # Crear movimiento de egreso
        movement_out = Movement.objects.create(
            movement_type='OUT',
            content_type=ContentType.objects.get_for_model(purchase),
            object_id=purchase.id,
            user=purchase.user,
            description=f"Egreso por anulación de compra #{purchase.id}"
        )
        for item in movement_in.items.all():
            MovementItem.objects.create(
                movement=movement_out,
                product=item.product,
                quantity=item.quantity  # misma cantidad que el ingreso
            )
            # Actualizar stock
            item.product.stock -= item.quantity
            item.product.save()
        return movement_out
    return None

# No se puede eliminar una compra, solo se puede anular
@login_required
def cancelled_purchase(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        purchase.status = 'cancelled'
        purchase.save()
        revert_purchase_movement(purchase)
        messages.success(request, "Compra anulada y stock revertido correctamente.")
        return redirect('purchase_list')
    return render(request, 'inv/purchase/cancelled_purchase.html', {
        'purchase': purchase,
    })

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
    context = {
        'purchase': purchase,
        'details': details,
        'title': 'Compra',
        'subtitle': 'Detalles de la compra',
        'icon': 'fa-shopping-cart',
    }
    
    return render(request, 'inv/purchase/purchase.html', context)

def create_purchase_movement(purchase):
    if purchase.status != 'confirmed':
        return None  # Solo crea movimiento si está confirmado

    # Verificar si ya se creó un movimiento para evitar duplicados y enviar mensaje de error
    if hasattr(purchase, 'movement') and purchase.movement:
        messages.error("Ya se ha creado un movimiento para esta compra.")
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
            quantity=detail.quantity
        )

        # Actualizar stock del producto
        detail.product.stock += detail.quantity
        
        # Actualizar costo de producto
        detail.product.cost = detail.unit_price
        
        # Actualizar precio de venta del producto
        detail.product.precio = detail.sale_price
        
        detail.product.save()
        
    return movement

# MOVIMIENTOS DE INVENTARIO
@login_required
def movement_list(request):
    product_id = request.GET.get('producto_id')
    movements = Movement.objects.all().order_by('-id', '-date')
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
    if request.method == 'POST':
        form = InventoryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data['archivo']
            nombre_archivo = archivo.name.lower()
            errores = []
            items_a_crear = []
            # Solo aceptar archivos .xlsx
            if nombre_archivo.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(archivo)
                ws = wb.active
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    product_code = row[0]
                    quantity = row[1]
                    cost = row[2] if len(row) > 2 else None
                    precio = row[3] if len(row) > 3 else None
                    location = row[4] if len(row) > 4 else None
                    try:
                        producto_id = Producto.objects.filter(nombre=product_code).values_list('id', flat=True).first()
                        producto = Producto.objects.get(id=producto_id)
                        items_a_crear.append((producto, quantity, cost, precio, location))
                    except Producto.DoesNotExist:
                        errores.append(f"Línea {i}: Producto con código '{product_code}' no existe.")
            else:
                errores.append("Solo se permiten archivos Excel (.xlsx).")

            if errores:
                from django.contrib import messages
                for error in errores:
                    messages.error(request, error)
                return render(request, 'inv/movement/cargar_inventario.html', {'form': form})

            # Si no hubo errores, ahora sí crea el movimiento y los items
            movimiento = Movement.objects.create(
                movement_type='IN',
                description='Inventario inicial',
                user=request.user
            )
            for producto, quantity, cost, precio, location in items_a_crear:
                MovementItem.objects.create(
                    movement=movimiento,
                    product=producto,
                    quantity=int(quantity)
                )
                # Actualizar stock del producto
                producto.stock = (producto.stock or 0) + int(quantity)
                # Actualizar cost y precio si vienen en el archivo
                if cost is not None:
                    producto.cost = cost
                if precio is not None:
                    producto.precio = precio
                if location is not None:
                    producto.location = location
                producto.save()
            from django.contrib import messages
            messages.success(request, "Inventario inicial cargado correctamente.")
            return redirect('movement_detail', movimiento.id)
    else:
        form = InventoryUploadForm()
    return render(request, 'inv/movement/cargar_inventario.html', {'form': form})

import json
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from .models import Movement, MovementItem, Producto

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
