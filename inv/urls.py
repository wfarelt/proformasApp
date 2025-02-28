from django.urls import path
from .views import MovementListView, DeleteView, create_movement\
    #movement_new, agregar_producto_a_movimiento, movement_edit, eliminar_producto_de_movimiento, 
    
urlpatterns = [
    path('movements/', MovementListView.as_view(), name='movement_list'),
    path('movements/new/', create_movement, name='create_movement'),
]
