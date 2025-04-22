from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import Purchase, Movement, MovementItem, Producto


@receiver(post_save, sender=Purchase)
def create_movement_on_purchase_confirmed(sender, instance, created, **kwargs):
    # Verificar que la compra ha sido confirmada y no es nueva
    if not created and instance.status == 'confirmed':
        # Crear un movimiento de tipo IN (Ingreso)
        movement = Movement.objects.create(
            movement_type='IN',
            description=f"Ingreso por compra #{instance.id} de {instance.supplier.name}",
            user=instance.user,
            status='COMPLETED',
            content_type=ContentType.objects.get_for_model(Purchase),
            object_id=instance.id
        )

        # Crear los MovementItems correspondientes a cada detalle de la compra
        for detail in instance.details.all():
            MovementItem.objects.create(
                movement=movement,
                product=detail.product,
                quantity=detail.quantity
            )
