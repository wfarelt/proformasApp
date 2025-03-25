from django.urls import path
from inv.views import *
    
urlpatterns = [
    # MOVIMIENTOS
    path('movements/', MovementListView.as_view(), name='movement_list'),
    path('movements/new/', create_movement, name='create_movement'),
    # INGRESOS
    path('ingresos/', ProductEntryListView.as_view(), name='product_entry'),
    path('ingresos/nuevo/', create_product_entry, name='create_product_entry'),   
    path('ingresos/editar/<int:pk>/', update_product_entrey, name='update_product_entry'),
    
    path('buscar-producto/', product_search, name='product_search'),
    
   # REPORTES
    path("reporte/productos-mas-vendidos/", reporte_productos_mas_vendidos, name="reporte_productos_mas_vendidos"),
    path("reporte/historial-ventas/", historial_ventas_producto, name="historial_ventas"),
    path('api/productos/', buscar_productos, name='buscar_productos'),
]
