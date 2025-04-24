from django.contrib import admin
from .models import Purchase, PurchaseDetail, Movement, MovementItem

# Register your models here.

# COMPRAS

class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'date', 'total_amount', 'invoice_number', 'status')
    list_filter = ('supplier', 'date', 'status')
    search_fields = ('supplier__name', 'invoice_number')
    
admin.site.register(Purchase, PurchaseAdmin)

admin.site.register(PurchaseDetail)

# MOVIMIENTOS

admin.site.register(Movement)

admin.site.register(MovementItem)

