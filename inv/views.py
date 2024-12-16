from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import View
from .forms import MovementDetailFormSet, MovementForm
from .models import Movement, MovementDetail
from core.models import Producto
from django.core.paginator import Paginator



class MovementListView(ListView):
    model = Movement
    template_name = 'inv/movement_list.html'
    context_object_name = 'movements'

class MovementCreateView(View):
    template_name = 'inv/movement_form.html'

    def get(self, request):
        # Formularios para el movimiento y sus detalles
        form = MovementForm()  # Si no tienes uno, usa un formulario básico para Movement
        formset = MovementDetailFormSet()
        return render(request, self.template_name, {'form': form, 'formset': formset})

    def post(self, request):
        form = MovementForm(request.POST)
        formset = MovementDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            movement = form.save()
            # Guardar los detalles con el movimiento relacionado
            details = formset.save(commit=False)
            for detail in details:
                detail.movement = movement
                detail.save()
            return redirect('movement_list')  # Redirige a la lista de movimientos

        # Si hay errores, volver a mostrar el formulario
        return render(request, self.template_name, {'form': form, 'formset': formset})

class MovementUpdateView(UpdateView):
    model = Movement
    template_name = 'inv/movement_form.html'

    def get(self, request, pk):
        movement = get_object_or_404(Movement, pk=pk)
        form = MovementForm(instance=movement)
        formset = MovementDetailFormSet(instance=movement)
        return render(request, self.template_name, {'form': form, 'formset': formset})
 
    def post(self, request, pk):
        movement = get_object_or_404(Movement, pk=pk)
        form = MovementForm(request.POST, instance=movement)
        formset = MovementDetailFormSet(request.POST, instance=movement)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('movement_list')
        
        return render(request, self.template_name, {'form': form, 'formset': formset})

class MovementDeleteView(DeleteView):
    model = Movement
    template_name = 'inv/movement_confirm_delete.html'
    success_url = reverse_lazy('movement_list')


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