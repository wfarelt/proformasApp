from collections import defaultdict

from django.db import transaction

from core.services.inventory_service import apply_warehouse_stock_change
from inv.models import Movement, MovementItem, StockTransfer, StockTransferItem


def create_warehouse_transfer(*, origin_warehouse, destination_warehouse, items, user, description=''):
    """Move inventory between warehouses and preserve both sides of the audit trail."""
    if origin_warehouse.pk == destination_warehouse.pk:
        raise ValueError('El almacén de origen y destino deben ser diferentes.')
    if not items:
        raise ValueError('Debes agregar al menos un producto.')

    grouped_items = defaultdict(lambda: {'product': None, 'quantity': 0, 'observations': []})
    for item in items:
        product = item['product']
        quantity = int(item['quantity'])
        if quantity <= 0:
            raise ValueError(f'La cantidad de {product.nombre} debe ser mayor que cero.')

        grouped_item = grouped_items[product.pk]
        grouped_item['product'] = product
        grouped_item['quantity'] += quantity
        observation = (item.get('observation') or '').strip()
        if observation:
            grouped_item['observations'].append(observation)

    with transaction.atomic():
        transfer = StockTransfer.objects.create(
            origin_warehouse=origin_warehouse,
            destination_warehouse=destination_warehouse,
            description=description,
            user=user,
        )
        movement_description = (
            f'Transferencia #{transfer.id}: {origin_warehouse.name} a {destination_warehouse.name}'
        )
        if description:
            movement_description = f'{movement_description}. {description}'

        outbound_movement = Movement.objects.create(
            movement_type='OUT',
            warehouse=origin_warehouse,
            transfer=transfer,
            description=movement_description,
            user=user,
            status='COMPLETED',
        )
        inbound_movement = Movement.objects.create(
            movement_type='IN',
            warehouse=destination_warehouse,
            transfer=transfer,
            description=movement_description,
            user=user,
            status='COMPLETED',
        )

        for grouped_item in grouped_items.values():
            product = grouped_item['product']
            quantity = grouped_item['quantity']
            observation = ' | '.join(grouped_item['observations'])

            origin_stock = apply_warehouse_stock_change(product, origin_warehouse, -quantity)
            destination_stock = apply_warehouse_stock_change(product, destination_warehouse, quantity)
            StockTransferItem.objects.create(
                transfer=transfer,
                product=product,
                quantity=quantity,
                observation=observation,
            )

            MovementItem.objects.create(
                movement=outbound_movement,
                product=product,
                quantity=quantity,
                unit_price=product.cost,
                stock_after_movement=origin_stock.quantity,
                observation=observation,
            )
            MovementItem.objects.create(
                movement=inbound_movement,
                product=product,
                quantity=quantity,
                unit_price=product.cost,
                stock_after_movement=destination_stock.quantity,
                observation=observation,
            )

    return transfer
