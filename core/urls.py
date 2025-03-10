# core/urls.py

from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from core.views import *

urlpatterns = [
    
    path('login/', LoginView.as_view(template_name='core/registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    #path('', Home2.as_view(), name='home2'),
    
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
    path('proforma/cambiar_estado_proforma/<int:id>/', cambiar_estado_proforma, name='cambiar_estado_proforma'),
    path('proforma/view/<int:id>/', proforma_view, name='proforma_view'),

    #clientes
    #path('clientes/', clientes_list, name='clientes_list'),
    path('clientes/', ClientListView.as_view(), name='client_list'),
    path('cliente/new/', cliente_new, name='cliente_new'),
    path('cliente/edit/<int:id>/', cliente_edit, name='cliente_edit'),
    path('cliente/delete/<int:id>/', cliente_delete, name='cliente_delete'),
    path('cliente/crear_clientes/', crear_clientes, name='crear_clientes'),
    #reporte pdf
    path('proforma/pdf/<int:id>', generate_proforma_pdf, name='generate_proforma_pdf'),
    path('reportes/', reportes, name='reportes'),
    #supplier
    path('suppliers/', SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/new/', supplier_create, name='supplier_create'),
    path('suppliers/edit/<int:pk>/', supplier_update, name='supplier_update'),
    #brand
    path('brands/', BrandListView.as_view(), name='brand_list'),
    path('brands/new/', brand_create, name='brand_create'),
    path('brands/edit/<int:pk>/', brand_update, name='brand_update'),
    path('brands/status/<int:pk>/', brand_status, name='brand_status'),
    
]
