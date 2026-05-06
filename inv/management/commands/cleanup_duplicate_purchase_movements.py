from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count

from inv.models import Purchase, Movement
from core.models import Producto


class Command(BaseCommand):
    help = (
        "Limpia movimientos duplicados por compra (IN/OUT). "
        "Mantiene el primero y elimina extras, corrigiendo stock."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica cambios. Sin esta bandera solo muestra simulacion.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        purchase_ct = ContentType.objects.get_for_model(Purchase)

        duplicate_groups = (
            Movement.objects.filter(
                content_type=purchase_ct,
                object_id__isnull=False,
                movement_type__in=["IN", "OUT"],
            )
            .values("object_id", "movement_type")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .order_by("object_id", "movement_type")
        )

        group_count = duplicate_groups.count()
        if group_count == 0:
            self.stdout.write(self.style.SUCCESS("No se encontraron duplicados de movimientos por compra."))
            return

        mode_label = "APLICAR" if apply_changes else "SIMULACION"
        self.stdout.write(self.style.WARNING(f"Modo: {mode_label}"))

        removed_movement_ids = []
        stock_adjustments = {}
        processed_groups = 0

        context_manager = transaction.atomic if apply_changes else _noop_context
        with context_manager():
            for group in duplicate_groups:
                purchase_id = group["object_id"]
                movement_type = group["movement_type"]

                movements = list(
                    Movement.objects.filter(
                        content_type=purchase_ct,
                        object_id=purchase_id,
                        movement_type=movement_type,
                    )
                    .prefetch_related("items")
                    .order_by("id")
                )

                keep_movement = movements[0]
                duplicate_movements = movements[1:]

                self.stdout.write(
                    f"Compra #{purchase_id} ({movement_type}): mantener #{keep_movement.id}, "
                    f"eliminar {[m.id for m in duplicate_movements]}"
                )

                for movement in duplicate_movements:
                    for item in movement.items.all():
                        delta = -item.quantity if movement_type == "IN" else item.quantity
                        stock_adjustments[item.product_id] = stock_adjustments.get(item.product_id, 0) + delta

                    removed_movement_ids.append(movement.id)
                    if apply_changes:
                        movement.delete()

                processed_groups += 1

            if apply_changes:
                for product_id, delta in stock_adjustments.items():
                    if delta == 0:
                        continue
                    product = Producto.objects.filter(pk=product_id).first()
                    if not product:
                        continue
                    current_stock = product.stock or 0
                    product.stock = current_stock + delta
                    product.save(update_fields=["stock"])

        self.stdout.write("")
        self.stdout.write(f"Grupos procesados: {processed_groups}")
        self.stdout.write(f"Movimientos duplicados: {len(removed_movement_ids)}")

        if stock_adjustments:
            self.stdout.write("Ajustes de stock por producto:")
            for product_id, delta in sorted(stock_adjustments.items()):
                if delta != 0:
                    sign = "+" if delta > 0 else ""
                    self.stdout.write(f"  Producto #{product_id}: {sign}{delta}")

        if apply_changes:
            self.stdout.write(self.style.SUCCESS("Limpieza aplicada correctamente."))
        else:
            self.stdout.write(self.style.WARNING("Simulacion finalizada. Ejecuta con --apply para aplicar."))


class _noop_context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False
