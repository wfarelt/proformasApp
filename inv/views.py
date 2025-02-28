from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import View
#from .forms import MovementDetailFormSet, MovementForm
from .models import Movement, MovementDetail
from core.models import Producto
from django.core.paginator import Paginator
from django.contrib import messages

from django.shortcuts import render, redirect
from django.forms import inlineformset_factory
from .models import Movement, MovementDetail
from .forms import MovementForm, MovementDetailForm

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
