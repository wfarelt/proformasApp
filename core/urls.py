# core/urls.py

from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView
from .views import CustomPasswordChangeView

from core.views import *

urlpatterns = [
    
    path('login/', LoginView.as_view(template_name='core/registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', PasswordChangeDoneView.as_view(
        template_name='core/registration/password_change_done.html'), name='password_change_done'),
    path('perfil/editar/', edit_profile, name='edit_profile'),
        
    path('', home, name='home'),
    #productos
    path('producto/<int:id>/', product_detail, name='product_detail'),
    path('producto/new/', producto_new, name='producto_new'),
    path('producto/edit/<int:id>/', product_edit, name='product_edit'),
    path('productos/', ProductListView.as_view(), name='product_list'),
    path('product/price/approve/<int:ph_id>/', approve_price, name='approve_price'),
    path('product/price/reject/<int:ph_id>/', reject_price, name='reject_price'),
    

    #proformas
    path('proformas/', ProformaListView.as_view(), name='proforma_list'),
    path('proforma/new/', proforma_new, name='proforma_new'),
    path('proforma/edit/<int:id>/', proforma_edit, name='proforma_edit'),
    path('proforma/agregar_producto_a_detalle/', agregar_producto_a_detalle, name='agregar_producto_a_detalle'),
    path('proforma/eliminar_producto_a_detalle/<int:id>/', eliminar_producto_a_detalle, name='eliminar_producto_a_detalle'),
    path('editar_cantidad_detalle/<int:detalle_id>/', editar_cantidad_detalle, name="editar_cantidad_detalle"),
    path('proforma/<int:id>/anular/', anular_proforma, name='anular_proforma'),
    
    path('proforma/add_client/<int:id>/', proforma_add_client, name='proforma_add_client'),
    path('proforma/cambiar_estado_proforma/<int:id>/', cambiar_estado_proforma, name='cambiar_estado_proforma'),
    path('proforma/view/<int:id>/', proforma_view, name='proforma_view'),
    path('proforma/<int:proforma_id>/pdf/', proforma_pdf, name='proforma_pdf'),
    path('proforma/<int:proforma_id>/almacen/', proforma_almacen, name='proforma_almacen'),
    path('proforma/<int:id>/cambiar_fecha/', cambiar_fecha_proforma, name='cambiar_fecha_proforma'),

    #clientes
    #path('clientes/', clientes_list, name='clientes_list'),
    path('clientes/', ClientListView.as_view(), name='client_list'),
    path('cliente/new/', cliente_new, name='cliente_new'),
    path('cliente/edit/<int:id>/', cliente_edit, name='cliente_edit'),
    path('cliente/delete/<int:id>/', cliente_delete, name='cliente_delete'),
    path('cliente/crear_clientes/', crear_clientes, name='crear_clientes'),
    path('cliente/cambio_estado/<int:id>/', cliente_status, name='cliente_status'),
    
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
    #product kits
    path('kits/', ProductKitListView.as_view(), name='kit_list'),
    path('kits/new/', kit_create, name='kit_create'),
    path('kits/<int:pk>/', kit_detail, name='kit_detail'),
    path('kits/<int:pk>/edit/', kit_edit, name='kit_edit'),
    path('kits/<int:pk>/delete/', kit_delete, name='kit_delete'),
    path('kits/<int:pk>/add-item/', kit_add_item, name='kit_add_item'),
    path('kits/<int:pk>/remove-item/<int:item_id>/', kit_remove_item, name='kit_remove_item'),
    path('api/kits/<int:kit_id>/items/', get_kit_items, name='get_kit_items'),
]
