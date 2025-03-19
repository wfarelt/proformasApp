from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import View
#from .forms import MovementDetailFormSet, MovementForm
from .models import Movement, MovementDetail, ProductEntry, ProductEntryDetail, Producto
from core.models import Producto
from django.core.paginator import Paginator
from django.contrib import messages

from django.forms import inlineformset_factory
from .forms import MovementForm, MovementDetailForm, ProductEntryForm, ProductEntryDetailForm




class MovementListView(ListView):
    model = Movement
    template_name = 'inv/movement_list.html'
    context_object_name = 'movements'
    
    # Ordenar por id de movimiento
    def get_queryset(self):
        return Movement.objects.all().order_by('-id')
   
def create_movement(request):
    MovementDetailFormSet = inlineformset_factory(Movement, MovementDetail, form=MovementDetailForm, extra=2, can_delete=True)
    
    if request.method == "POST":
        form = MovementForm(request.POST)
        formset = MovementDetailFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            movement = form.save()
            formset.instance = movement
            formset.save()
            return redirect('movement_list')
    
    else:
        form = MovementForm()
        formset = MovementDetailFormSet()

    return render(request, 'inv/movement_form.html', {'form': form, 'formset': formset})

# INGRESOS

class ProductEntryListView(ListView):
    model = ProductEntry
    template_name = 'inv/productEntry/product_entry_list.html'
    context_object_name = 'entries'
    paginate_by = 10
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Ingresos'
        context['placeholder'] = 'Buscar por descripción'
        return context
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        object_list = ProductEntry.objects.all().order_by('-id')
        if query:
            object_list = object_list.filter(description__icontains=query)
        return object_list

def create_product_entry(request):
    ProductEntryDetailFormSet = inlineformset_factory(
        ProductEntry, ProductEntryDetail, form=ProductEntryDetailForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        entry_form = ProductEntryForm(request.POST)
        # Guardar usuario que realiza el ingreso
        entry_form.instance.user = request.user
        formset = ProductEntryDetailFormSet(request.POST)

        if entry_form.is_valid() and formset.is_valid():
            
            entry = entry_form.save()

            for form in formset:
                if form.cleaned_data.get('product') and form.cleaned_data.get('quantity'):
                    detail = form.save(commit=False)
                    detail.entry = entry
                    detail.save()

                    if entry.status == 'confirmed':
                        # Actualizar stock del producto
                        product = detail.product
                        product.stock += detail.quantity
                        product.save()
            
            messages.success(request, 'Ingreso actualizado correctamente.')
            return redirect('product_entry')
        
        else:
            messages.error(request, 'Error al guardar el ingreso. Verifique los datos ingresados.')
        
    else:
        entry_form = ProductEntryForm()
        formset = ProductEntryDetailFormSet()

    return render(request, 'inv/productEntry/product_entry_form.html', {'entry_form': entry_form, 'formset': formset})


def update_product_entrey(request, pk):
    
    entry = get_object_or_404(ProductEntry, pk=pk)
    ProductEntryDetailFormSet = inlineformset_factory(
        ProductEntry, ProductEntryDetail, form=ProductEntryDetailForm, extra=0, can_delete=True
    )

    if request.method == "POST":
        entry_form = ProductEntryForm(request.POST, instance=entry)
        # Guardar usuario que realiza el ingreso
        entry_form.instance.user = request.user
        formset = ProductEntryDetailFormSet(request.POST, instance=entry)

        if entry_form.is_valid() and formset.is_valid():
            entry = entry_form.save()
            # Eliminar detalles de ingreso
            ProductEntryDetail.objects.filter(entry=entry).delete()
            
            for form in formset:
                
                if form.cleaned_data.get('product') and form.cleaned_data.get('quantity'):
                    detail = form.save(commit=False)
                    detail.entry = entry
                    detail.save()

                    if entry.status == 'confirmed':
                        # Actualizar stock del producto
                        product = detail.product
                        product.stock += detail.quantity
                        product.save()
            
            messages.success(request, 'Ingreso actualizado correctamente.')

            return redirect('product_entry')
        
        else:
            messages.error(request, 'Error al editar el ingreso. Verifique los datos ingresados.' + str(entry_form.errors) + str(formset.errors))

    else:
        entry_form = ProductEntryForm(instance=entry)
        formset = ProductEntryDetailFormSet(instance=entry)

    return render(request, 'inv/productEntry/product_entry_form.html', {'entry_form': entry_form, 'formset': formset})