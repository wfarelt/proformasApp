from django.contrib import admin
from .models import Producto, Proforma, Cliente, Detalle


admin.site.register(Producto)

admin.site.register(Proforma)

admin.site.register(Detalle)

admin.site.register(Cliente)