from django.urls import path
from inv.views import *
    
urlpatterns = [
    
    # INGRESOS
   # path('entries/', entry_list, name='entry_list'),
   # path('entries/create/', entry_create, name='entry_create'),
   # path('entries/<int:pk>/edit/', entry_update, name='entry_update'),
   # path('entries/<int:pk>/delete/', entry_delete, name='entry_delete'),
   # path('buscar-producto/', product_search, name='product_search'),
    
   # REPORTES
    path("reporte/productos-mas-vendidos/", reporte_productos_mas_vendidos, name="reporte_productos_mas_vendidos"),
    path("reporte/historial-ventas/", historial_ventas_producto, name="historial_ventas"),
    path("api/productos/", buscar_productos, name="buscar_productos"),
    path("reporte/reporte-inventario/", reporte_inventario, name="reporte_inventario"),
    path('reportes/proformas/', proforma_report, name='proforma_report'),
    path('pre-inventario/', pre_inventario, name='pre_inventario'),
    
    # COMPRAS
    path('compras/', purchase_list, name='purchase_list'),
    path('compras/nueva/', create_purchase, name='create_purchase'),
    path('compras/<int:pk>/editar/', update_purchase, name='update_purchase'),
    path('compras/<int:pk>/detalle/', purchase_detail, name='purchase_detail'),    
    path('compras/<int:pk>/anular/', cancelled_purchase, name='cancelled_purchase'),
    
    # MOVIMIENTOS
    path('movimientos/', movement_list, name='movement_list'),
    #movimiento_detail
    path('movimientos/<int:pk>/detalle', movement_detail, name='movement_detail'),
    path('movimientos/nuevo2/', create_movement, name='create_movement'),
    path('inventario/cargar/', cargar_inventario_inicial, name='cargar_inventario_inicial'),
    path('api/producto/<int:id>/', get_producto, name='get_producto'),
    path('movimientos/<int:pk>/pdf/', movement_pdf, name='movement_pdf'),
    path('movimientos/nuevo/', CreateMovementView.as_view(), name='create_movement_json'),

    
]

