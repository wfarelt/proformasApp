from django.db import transaction
from django.db.models import F, Sum

from core.models import ProductStock


class InsufficientWarehouseStock(ValueError):
    pass


def apply_warehouse_stock_change(product, warehouse, quantity_delta, location=None):
    """Aplica un cambio de inventario y mantiene el total legacy sincronizado."""
    if quantity_delta == 0:
        return ProductStock.objects.get(product=product, warehouse=warehouse)

    with transaction.atomic():
        stock, _ = ProductStock.objects.select_for_update().get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={'quantity': 0, 'location': location or ''},
        )

        if stock.quantity + quantity_delta < 0:
            raise InsufficientWarehouseStock(
                f'Stock insuficiente en {warehouse.name} para el producto {product.nombre}. '
                f'Disponible: {stock.quantity}, solicitado: {abs(quantity_delta)}.'
            )

        stock.quantity = F('quantity') + quantity_delta
        update_fields = ['quantity', 'updated_at']
        if location is not None:
            stock.location = location
            update_fields.append('location')
        stock.save(update_fields=update_fields)
        stock.refresh_from_db(fields=['quantity', 'location'])

        total_stock = ProductStock.objects.filter(product=product).aggregate(total=Sum('quantity'))['total'] or 0
        product.stock = total_stock
        product.save(update_fields=['stock'])
        return stock