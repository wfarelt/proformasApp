# core/urls.py

from django.urls import path
from .views import home, ProformaListView, proforma_add_client , proforma_new, proforma_edit,\
    agregar_producto_a_detalle, producto_new, eliminar_producto_a_detalle, \
        cliente_new, cliente_edit, cliente_delete, ClientListView,\
            product_detail, product_edit, ProductListView, generate_proforma_pdf, \
                reportes, \
                    SupplierListView, supplier_create, supplier_update

urlpatterns = [
    path('', home, name='home'),
    #productos
    path('producto/<int:id>/', product_detail, name='product_detail'),
    path('producto/new/', producto_new, name='producto_new'),
    path('producto/edit/<int:id>/', product_edit, name='product_edit'),
    path('productos/', ProductListView.as_view(), name='product_list'),
    #proformas
    path('proformas/', ProformaListView.as_view(), name='proforma_list'),
    path('proforma/new/', proforma_new, name='proforma_new'),
    path('proforma/edit/<int:id>/', proforma_edit, name='proforma_edit'),
    path('proforma/agregar_producto_a_detalle/', agregar_producto_a_detalle, name='agregar_producto_a_detalle'),
    path('proforma/eliminar_producto_a_detalle/<int:id>/', eliminar_producto_a_detalle, name='eliminar_producto_a_detalle'),
    path('proforma/add_client/<int:id>/', proforma_add_client, name='proforma_add_client'),
    #clientes
    #path('clientes/', clientes_list, name='clientes_list'),
    path('clientes/', ClientListView.as_view(), name='client_list'),
    path('cliente/new/', cliente_new, name='cliente_new'),
    path('cliente/edit/<int:id>/', cliente_edit, name='cliente_edit'),
    path('cliente/delete/<int:id>/', cliente_delete, name='cliente_delete'),
    #reporte pdf
    path('proforma/pdf/<int:id>', generate_proforma_pdf, name='generate_proforma_pdf'),
    path('reportes/', reportes, name='reportes'),
    #supplier
    path('suppliers/', SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/new/', supplier_create, name='supplier_create'),
    path('suppliers/edit/<int:pk>/', supplier_update, name='supplier_update'),
]
