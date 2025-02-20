from django.urls import path
from .views import MovementListView, DeleteView, \
    movement_new, agregar_producto_a_movimiento, movement_edit, eliminar_producto_de_movimiento

urlpatterns = [
    path('movements/', MovementListView.as_view(), name='movement_list'),
    path('movements/new/', movement_new, name='movement_new'),
    path('movements/edit/<int:pk>/', movement_edit, name='movement_edit'),
    path('movements/add_product/', agregar_producto_a_movimiento, name='agregar_producto_a_movimiento'),
    path('movements/delete_product/<int:pk>/', eliminar_producto_de_movimiento, name='eliminar_producto_de_movimiento'),
    path('movements/delete/<int:pk>/', DeleteView.as_view(), name='movement_delete'),

]
