from django.contrib import admin
from .models import ProductEntry, ProductEntryDetail

# Register your models here.

# INGRESOS

admin.site.register(ProductEntry)

# Mostrar el detalle de ingreso en el admin (Id, fecha, tipo, proveedor, cantidad total)        
class ProductEntryDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'entry', 'product', 'quantity')
    list_filter = ('entry',)
    search_fields = ('product__name',)

admin.site.register(ProductEntryDetail, ProductEntryDetailAdmin)
