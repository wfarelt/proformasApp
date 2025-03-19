from django.urls import path
from inv.views import MovementListView, create_movement, ProductEntryListView, create_product_entry, \
    update_product_entrey
    
urlpatterns = [
    # MOVIMIENTOS
    path('movements/', MovementListView.as_view(), name='movement_list'),
    path('movements/new/', create_movement, name='create_movement'),
    # INGRESOS
    path('ingresos/', ProductEntryListView.as_view(), name='product_entry'),
    path('ingresos/nuevo/', create_product_entry, name='create_product_entry'),   
    path('ingresos/editar/<int:pk>/', update_product_entrey, name='update_product_entry'),
]
