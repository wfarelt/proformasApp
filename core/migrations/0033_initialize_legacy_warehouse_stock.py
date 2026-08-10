from django.db import migrations


LEGACY_WAREHOUSE_CODE = 'LEGACY'


def initialize_legacy_warehouse_stock(apps, schema_editor):
    Warehouse = apps.get_model('core', 'Warehouse')
    ProductStock = apps.get_model('core', 'ProductStock')
    Producto = apps.get_model('core', 'Producto')

    warehouse = Warehouse.objects.filter(
        company__isnull=True,
        code=LEGACY_WAREHOUSE_CODE,
    ).first()
    if warehouse is None:
        warehouse = Warehouse.objects.create(
            name='Almacen principal',
            code=LEGACY_WAREHOUSE_CODE,
            is_default=True,
        )

    product_stocks = []
    for product in Producto.objects.all().iterator():
        product_stocks.append(
            ProductStock(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=product.stock or 0,
                location=product.location or '',
            )
        )

    ProductStock.objects.bulk_create(
        product_stocks,
        batch_size=1000,
        ignore_conflicts=True,
    )


def reverse_initialize_legacy_warehouse_stock(apps, schema_editor):
    Warehouse = apps.get_model('core', 'Warehouse')
    ProductStock = apps.get_model('core', 'ProductStock')

    warehouses = Warehouse.objects.filter(
        company__isnull=True,
        code=LEGACY_WAREHOUSE_CODE,
    )
    ProductStock.objects.filter(warehouse__in=warehouses).delete()
    warehouses.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_add_warehouses'),
    ]

    operations = [
        migrations.RunPython(
            initialize_legacy_warehouse_stock,
            reverse_initialize_legacy_warehouse_stock,
        ),
    ]
