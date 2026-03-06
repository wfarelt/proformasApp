from django import template
from core.models import ProductPriceHistory

register = template.Library()


@register.simple_tag
def pending_price_history(limit=5):
    """Return a queryset of pending ProductPriceHistory limited by `limit`."""
    try:
        return ProductPriceHistory.objects.filter(status='PENDING').select_related('product').order_by('-created_at')[:limit]
    except Exception:
        return []


@register.filter
def get_dict_item(dictionary, key):
    """Obtiene un valor de diccionario por clave de forma segura."""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)
