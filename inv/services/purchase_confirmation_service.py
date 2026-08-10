from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from core.services.inventory_service import apply_warehouse_stock_change
from core.services.purchase_price_service import create_price_history_from_purchase
from inv.models import Movement, MovementItem, Purchase


def confirm_purchase_and_apply_inventory(purchase, user=None):
    """
    Confirma y aplica inventario de una compra de forma idempotente.

    Reglas:
    - Solo procesa compras en estado confirmed.
    - Si ya existe movimiento IN para la compra, no duplica efectos.
    - Actualiza stock y costo del producto por cada detalle.
    - Genera historial de precios una sola vez en la misma ruta.
    """
    with transaction.atomic():
        purchase_locked = (
            Purchase.objects.select_for_update()
            .select_related("supplier", "user")
            .prefetch_related("details__product")
            .get(pk=purchase.pk)
        )

        if purchase_locked.status != "confirmed":
            return None
        if purchase_locked.warehouse_id is None:
            raise ValueError('La compra debe tener un almacén de ingreso asignado.')

        ct = ContentType.objects.get_for_model(Purchase)
        existing_movement = Movement.objects.filter(
            content_type=ct,
            object_id=purchase_locked.id,
            movement_type="IN",
        ).first()
        if existing_movement:
            return existing_movement

        movement = Movement.objects.create(
            movement_type="IN",
            warehouse=purchase_locked.warehouse,
            content_type=ct,
            object_id=purchase_locked.id,
            user=purchase_locked.user,
            description=f"Ingreso generado por la compra #{purchase_locked.id}",
        )

        for detail in purchase_locked.details.all():
            MovementItem.objects.create(
                movement=movement,
                product=detail.product,
                quantity=detail.quantity,
                unit_price=detail.unit_price,
            )

            apply_warehouse_stock_change(
                detail.product,
                purchase_locked.warehouse,
                detail.quantity,
            )
            detail.product.cost = detail.unit_price
            detail.product.save(update_fields=["cost"])

        create_price_history_from_purchase(purchase_locked, user or purchase_locked.user)

        return movement
