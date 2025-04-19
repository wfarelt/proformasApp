from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.timezone import now
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from datetime import timedelta

from core.models import Producto, Detalle, productos_mas_vendidos
from .models import ProductEntry, Producto, Purchase, PurchaseDetail
from .forms import ProductEntryForm, ProductEntryDetailFormSet, PurchaseForm, PurchaseDetailFormSet

from django.db import transaction

# INGRESOS

@login_required
def entry_list(request):
    entries = ProductEntry.objects.all().order_by('-date')
    return render(request, 'inv/entries/entry_list.html', {'entries': entries})

@login_required
def entry_create(request):
    if request.method == 'POST':
        form = ProductEntryForm(request.POST)
        formset = ProductEntryDetailFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user  # Asignar el usuario actual al ingreso
            entry.save()
            formset.instance = entry  # Asignar la instancia del ingreso al formset
            formset.save()
            
            if entry.status == 'confirmed':
                # Actualizar el stock de los productos ingresados
                for detail in formset:
                    if detail.cleaned_data and detail.cleaned_data.get('DELETE'):
                        # Actualizar el stock del producto
                        product = detail.cleaned_data['product']
                        quantity = detail.cleaned_data['quantity']
                        product.stock += quantity
                        product.save()
                # Mensaje de éxito
                messages.success(request, 'Ingreso registrado correctamente.')
            
            # Retornar a entry_update
            return redirect('entry_update', pk=entry.pk)
        else:
            # Mensaje de error
            messages.error(request, 'Error al registrar el ingreso. Por favor, revise los datos.')         
    else:
        form = ProductEntryForm()
        formset = ProductEntryDetailFormSet()

    return render(request, 'inv/entries/entry_form.html', {'form': form, 'formset': formset})

@login_required
def entry_update(request, pk):
    entry = get_object_or_404(ProductEntry, pk=pk)
    if request.method == 'POST':
        form = ProductEntryForm(request.POST, instance=entry)
        formset = ProductEntryDetailFormSet(request.POST, instance=entry)
               
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            # Si el estado es 'confirmed' enviar a entry_list, sino a entry_update
            if entry.status == 'confirmed':
                # Actualizar el stock de los productos ingresados
                for detail in formset:
                    if detail.cleaned_data and detail.cleaned_data.get('DELETE'):
                        product = detail.cleaned_data['product']
                        quantity = detail.cleaned_data['quantity']
                        product.stock += quantity
                        product.save()
                messages.success(request, 'Ingreso actualizado correctamente.')
                return redirect('entry_list')
            else:
                messages.success(request, 'Ingreso actualizado correctamente.')
                return redirect('entry_update', pk=pk)
        else:
            messages.error(request, 'Error al actualizar el ingreso. Por favor, revise los datos.')
    else:
        form = ProductEntryForm(instance=entry)
        formset = ProductEntryDetailFormSet(instance=entry)

    return render(request, 'inv/entries/entry_form.html', {'form': form, 'formset': formset})

@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(ProductEntry, pk=pk)
    if request.method == 'POST':
        entry.delete()
        return redirect('entry_list')
    return render(request, 'inv/entries/entry_confirm_delete.html', {'entry': entry})
        
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
    
    return render(request, "inv/reports/productos_mas_vendidos.html", {"productos": productos, "dias": dias})

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
        "dias": dias
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
        "productos": productos
    })

# COMPRAS

@login_required
def purchase_list(request):
    purchases = Purchase.objects.all().order_by('-status','-id', '-date')
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
                purchase.date = now()
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
                purchase.date = now()

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

# No se puede eliminar una compra, solo se puede anular
@login_required
def cancelled_purchase(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        purchase.status = 'cancelled'
        purchase.save()
        messages.success(request, "Compra anulada correctamente.")
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
    