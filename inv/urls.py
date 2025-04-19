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
    
    # COMPRAS
    path('compras/', purchase_list, name='purchase_list'),
    path('compras/nueva/', create_purchase, name='create_purchase'),
    path('compras/<int:pk>/editar/', update_purchase, name='update_purchase'),
    path('compras/<int:pk>/detalle/', purchase_detail, name='purchase_detail'),    
    path('compras/<int:pk>/anular/', cancelled_purchase, name='cancelled_purchase')
]

