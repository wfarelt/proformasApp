from django.urls import path
from inv.views import *
    
urlpatterns = [
    
    # INGRESOS
    path('entries/', entry_list, name='entry_list'),
    path('entries/create/', entry_create, name='entry_create'),
    path('entries/<int:pk>/edit/', entry_update, name='entry_update'),
    path('entries/<int:pk>/delete/', entry_delete, name='entry_delete'),

       
    path('buscar-producto/', product_search, name='product_search'),
    
   # REPORTES
    path("reporte/productos-mas-vendidos/", reporte_productos_mas_vendidos, name="reporte_productos_mas_vendidos"),
    path("reporte/historial-ventas/", historial_ventas_producto, name="historial_ventas"),
    path("api/productos/", buscar_productos, name="buscar_productos"),
    path("reporte/reporte-inventario/", reporte_inventario, name="reporte_inventario"),
]

