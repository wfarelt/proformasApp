from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import View
from .forms import MovementDetailFormSet, MovementForm
from .models import Movement, MovementDetail
from core.models import Producto
from django.core.paginator import Paginator
from django.contrib import messages

class MovementListView(ListView):
    model = Movement
    template_name = 'inv/movement_list.html'
    context_object_name = 'movements'
    
    # Ordenar por id de movimiento
    def get_queryset(self):
        return Movement.objects.all().order_by('-id')
    
def cambiar_estado_movimiento(request, pk):
    movimiento = get_object_or_404(Movement, pk=pk)
    movimiento.estado = not movimiento.estado
    movimiento.save()
    return redirect('movement_list')

# Crear proforma
def movement_new(request):
    query = request.GET.get('q')
    
    last_movement = Movement.objects.last()
    if last_movement and MovementDetail.productos_list(last_movement).count() < 1:
        movement = last_movement
    else:
        movement = Movement.objects.create()
    
    detalles = MovementDetail.productos_list(movement)
    productos_list = Producto.objects.all()

    
    if query:
        productos_list = productos_list.filter(nombre__icontains=query)
    
    paginator = Paginator(productos_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'movement': movement,
        'productos_list': page_obj,
        'detalles': detalles,
        'page_obj': page_obj,
    }

    return render(request, 'inv/movement_form.html', context)

# Editar movimiento
def movement_edit(request, pk):
    movement = Movement.objects.get(id=pk)
    detalles = MovementDetail.productos_list(movement)
    productos_list = Producto.objects.all()
    
    if request.method == 'POST':
        movement_type = request.POST.get('movement_type')
        movement.movement_type = movement_type
        movement.save()
        
    else:
    
        if query := request.GET.get('q'):
            productos_list = productos_list.filter(nombre__icontains=query)
            paginator = Paginator(productos_list, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            context = {'movement': movement, 'productos_list': page_obj, 'detalles': detalles, 'page_obj': page_obj}
        else:
            paginator = Paginator(productos_list, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            context = {'movement': movement, 'productos_list': page_obj, 'detalles': detalles, 'page_obj': page_obj}
        
    return render(request, 'inv/movement_form.html', context)

# Agregar producto a MovementDetail
def agregar_producto_a_movimiento(request):
        # VALIR DATOS SI ES POST O GET
    if request.method == 'POST':
        movement_id = request.POST.get('movement_id')
        movement_type = request.POST.get('movement_type')
        description = request.POST.get('description')	
        producto_id = request.POST.get('producto_id')
        quantity = request.POST.get('quantity')
        cost = request.POST.get('cost')
        # VALIDAR SI LOS CAMPOS ESTAN VACIOS
        if not quantity or int(quantity) <= 0:
            messages.error(request, f'No se puede agregar una cantidad menor o igual a 0.')
            return redirect(reverse_lazy('movement_edit', args=[movement_id]))
        if not cost or float(cost) <= 0:
            messages.error(request, f'No se puede agregar un precio menor o igual a 0.')
            return redirect(reverse_lazy('movement_edit', args=[movement_id]))
        #añadir a subtotal en float
        subtotal =  float(quantity) * float(cost)
        
        # ACTUALIZAR TOTAL DE MOVEMENT       
        movement = Movement.objects.get(id=movement_id)
        movement.movement_type = movement_type
        movement.description = description
        movement.total_quantity = float(movement.total_quantity) + float(subtotal) 
        movement.save()
        
        # CREAR DETALLE
        
        product = Producto.objects.get(id=producto_id)
        detalle = MovementDetail.objects.create(movement=movement, product=product, quantity=quantity, cost=cost , subtotal=subtotal)
        detalle.save()
        
        # REDIRECCIONAR A LA MISMA PAGINA
        return redirect(reverse_lazy('movement_edit', args=[movement_id]))
    else:
        return render(request, 'core/home.html')

# Eliminar producto de MovementDetail

def eliminar_producto_de_movimiento(request, pk):
    detalle = get_object_or_404(MovementDetail, pk=pk)
    movement_id = detalle.movement.id
    detalle.delete()
    return redirect(reverse_lazy('movement_edit', args=[movement_id]))

# Modificar Movement_Type [in, out]
def modificar_tipo_movimiento(request, pk, tipo):
    movimiento = get_object_or_404(Movement, pk=pk)
    movimiento.movement_type = tipo
    movimiento.save()
    return redirect(reverse_lazy('movement_edit', args=[pk]))

# Eliminar movimiento
class MovementDeleteView(DeleteView):
    model = Movement
    template_name = 'inv/movement_delete.html'
    success_url = reverse_lazy('movement_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = 'Eliminar movimiento'
        return context