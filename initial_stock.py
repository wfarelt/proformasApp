from django.db import transaction
from django.db.models import Sum
from core.models import Proforma, Producto, ProductStock, Warehouse
from inv.models import Purchase, Movement, MovementItem, StockTransfer

KEEP = 62

with transaction.atomic():
    keep = Movement.objects.get(pk=KEEP, movement_type='IN')
    print("Conservando:", keep, keep.warehouse, keep.items.count(), "items")

    # Proformas (Detalle se elimina en cascada)
    Proforma.objects.all().delete()

    # Compras (PurchaseDetail en cascada)
    Purchase.objects.all().delete()

    # Movimientos: quitar todos menos el #62
    Movement.objects.exclude(pk=KEEP).delete()   # MovementItem en cascada
    StockTransfer.objects.all().delete()          # items en cascada; ya no hay movimientos que las protejan

    # El #62 ya no tiene documento asociado (compra eliminada)
    keep.content_type = None
    keep.object_id = None
    keep.transfer = None
    keep.save()

    # Stock a cero
    ProductStock.objects.all().delete()
    Producto.objects.update(stock=0)

    # Stock real = items del movimiento #62
    wh = keep.warehouse or Warehouse.objects.first()
    for item in keep.items.all():
        ps, _ = ProductStock.objects.get_or_create(product=item.product, warehouse=wh)
        ps.quantity += item.quantity
        ps.save()
        item.stock_after_movement = ps.quantity
        item.save(update_fields=['stock_after_movement'])

    for p in Producto.objects.all():
        total = p.warehouse_stocks.aggregate(t=Sum('quantity'))['t'] or 0
        Producto.objects.filter(pk=p.pk).update(stock=total)