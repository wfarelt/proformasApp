from django.contrib import admin
from .models import Producto, Proforma, Cliente, Detalle, Brand, \
    Supplier
from import_export.admin import ImportExportModelAdmin
from .resources import ProductResource


admin.site.register(Proforma)

admin.site.register(Detalle)

admin.site.register(Cliente)

admin.site.register(Brand)

admin.site.register(Supplier)

class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource

admin.site.register(Producto, ProductAdmin)
