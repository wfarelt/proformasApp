from django.contrib import admin
from .models import Movement, MovementDetail, ProductEntry, ProductEntryDetail

# Register your models here.

class MovementDetailInline(admin.TabularInline):
    model = MovementDetail
    extra = 1

class MovementAdmin(admin.ModelAdmin):
    inlines = [MovementDetailInline]

admin.site.register(Movement, MovementAdmin)

# Mostrar el detalle de movimiento en el admin (Id, fecha, tipo, proveedor, cantidad total)
class MovementDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'movement', 'product', 'quantity', 'cost', 'subtotal')
    
admin.site.register(MovementDetail, MovementDetailAdmin)


admin.site.register(ProductEntry)

# Mostrar el detalle de ingreso en el admin (Id, fecha, tipo, proveedor, cantidad total)        
class ProductEntryDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'entry', 'product', 'quantity')
    list_filter = ('entry',)
    search_fields = ('product__name',)

admin.site.register(ProductEntryDetail, ProductEntryDetailAdmin)
