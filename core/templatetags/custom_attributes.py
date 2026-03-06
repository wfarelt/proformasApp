"""
Template tags para mostrar atributos personalizados
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_custom_attr(producto, attr_name):
    """
    Obtiene un atributo personalizado de un producto
    Uso en template: {{ producto|get_custom_attr:"color" }}
    """
    if not producto:
        return ''
    
    value = (producto.custom_attributes or {}).get(attr_name)
    
    # Si es None o vacío, retornar string vacío
    if value is None or value == '':
        return '-'
    
    return str(value)


@register.filter
def custom_attrs_table(producto):
    """
    Renderiza una tabla HTML con todos los atributos personalizados
    Uso en template: {{ producto|custom_attrs_table }}
    """
    if not producto:
        return ''
    
    attrs = producto.custom_attributes or {}
    display_values = [
        {
            'label': key.replace('_', ' ').title(),
            'value': value,
        }
        for key, value in attrs.items()
    ]
    
    if not display_values:
        return '<p class="text-muted">Sin atributos personalizados</p>'
    
    html = '<table class="table table-sm table-borderless">'
    
    for attr in display_values:
        html += f"""
        <tr>
            <td class="fw-bold">{attr['label']}:</td>
            <td>{attr['value'] or '-'}</td>
        </tr>
        """
    
    html += '</table>'
    return mark_safe(html)


@register.inclusion_tag('core/custom_attributes_list.html')
def render_custom_attributes(producto):
    """
    Renderiza los atributos personalizados usando un template
    Uso en template: {% render_custom_attributes producto %}
    """
    if not producto:
        return {'attributes': []}
    
    attrs = producto.custom_attributes or {}
    display_values = [
        {
            'name': key,
            'label': key.replace('_', ' ').title(),
            'value': value,
            'type': 'text',
        }
        for key, value in attrs.items()
    ]
    return {'attributes': display_values}
