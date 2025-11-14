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

class MovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'movement_type', 'user', 'date')
    list_filter = ('movement_type', )
    search_fields = ('movement_type',)
    
admin.site.register(Movement, MovementAdmin)

# MOVEMENT ITEMS
class MovementItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'movement_id', 'product', 'quantity', 'unit_price')
    search_fields = ('movement__id', )
    
    
admin.site.register(MovementItem, MovementItemAdmin)
