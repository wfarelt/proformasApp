from django.contrib import admin
from .models import Movement, MovementDetail

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


