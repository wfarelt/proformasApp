# core/services/price_approval_service.py

from django.utils import timezone
from core.models import Producto, ProductPriceHistory

class PriceApprovalService:

    @staticmethod
    def approve(price_history, approved_by):
        """
        Aprueba un ProductPriceHistory pendiente, expira el anterior y
        actualiza el Producto correspondiente.
        """
        if price_history.status != 'PENDING':
            raise ValueError('Solo se pueden aprobar precios con estado PENDING')

        product = price_history.product

        # Expirar precio vigente anterior
        previous = (
            product.price_history
            .filter(status='APPROVED')
            .first()
        )
        if previous:
            previous.status = 'EXPIRED'
            previous.valid_to = timezone.now()
            previous.save()

        # Aprobar nuevo precio
        price_history.status = 'APPROVED'
        price_history.valid_from = timezone.now()
        price_history.approved_by = approved_by
        price_history.save()

        # Actualizar Producto
        product.precio = price_history.new_price
        if price_history.cost_reference is not None:
            product.cost = price_history.cost_reference
        product.save()

        return price_history
