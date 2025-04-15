from django.contrib import admin
from .models import ProductEntry, ProductEntryDetail, Purchase, PurchaseDetail

# Register your models here.

# INGRESOS

admin.site.register(ProductEntry)

# Mostrar el detalle de ingreso en el admin (Id, fecha, tipo, proveedor, cantidad total)        
class ProductEntryDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'entry', 'product', 'quantity')
    list_filter = ('entry',)
    search_fields = ('product__name',)

admin.site.register(ProductEntryDetail, ProductEntryDetailAdmin)

# COMPRAS

class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'date', 'total_amount', 'invoice_number', 'status')
    list_filter = ('supplier', 'date', 'status')
    search_fields = ('supplier__name', 'invoice_number')
    
admin.site.register(Purchase, PurchaseAdmin)

admin.site.register(PurchaseDetail)