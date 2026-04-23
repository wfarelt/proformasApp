"""
Gestor para atributos personalizados de productos por empresa
"""
from typing import Dict, Any, List, Optional
from django.core.exceptions import ValidationError


class CustomAttributeConfig:
    """Clase para gestionar la configuración de atributos personalizados"""
    
    VALID_TYPES = ['text', 'number', 'date', 'boolean', 'select']
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        Valida que la configuración sea correcta
        
        Formato esperado:
        {
            "color": {
                "type": "text",
                "label": "Color",
                "required": False,
                "options": []  # para tipo 'select'
            },
            "garantia_meses": {
                "type": "number",
                "label": "Garantía (meses)",
                "required": True,
                "min": 0,
                "max": 60
            }
        }
        """
        if not isinstance(config, dict):
            raise ValidationError("La configuración debe ser un diccionario")
        
        for field_name, field_config in config.items():
            if not isinstance(field_config, dict):
                raise ValidationError(f"El campo '{field_name}' debe ser un diccionario")
            
            # Validar que tiene los campos obligatorios
            if 'type' not in field_config:
                raise ValidationError(f"El campo '{field_name}' debe tener un 'type'")
            
            if 'label' not in field_config:
                raise ValidationError(f"El campo '{field_name}' debe tener un 'label'")
            
            # Validar que el tipo es válido
            if field_config['type'] not in CustomAttributeConfig.VALID_TYPES:
                raise ValidationError(
                    f"El campo '{field_name}' tiene un tipo inválido. "
                    f"Tipos válidos: {', '.join(CustomAttributeConfig.VALID_TYPES)}"
                )
            
            # Validar opciones si es tipo 'select'
            if field_config['type'] == 'select' and 'options' in field_config:
                if not isinstance(field_config['options'], list):
                    raise ValidationError(f"El campo '{field_name}' debe tener 'options' como lista")
        
        return True
    
    @staticmethod
    def get_field_definition(config: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene la definición de un campo específico"""
        return config.get(field_name)
    
    @staticmethod
    def get_all_fields(config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtiene todos los campos con su configuración"""
        return [
            {
                'name': name,
                **definition
            }
            for name, definition in config.items()
        ]
    
    @staticmethod
    def validate_values(config: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Valida que los valores cumplan con la configuración
        
        Retorna diccionario con errores por campo
        """
        errors = {}
        
        # Los atributos personalizados se manejan como opcionales.
        for field_name, field_config in config.items():
            if field_name in values:
                value = values[field_name]
                
                # Validar por tipo
                if field_config['type'] == 'number':
                    try:
                        float(value)
                        if 'min' in field_config and float(value) < field_config['min']:
                            errors.setdefault(field_name, []).append(
                                f"El valor debe ser mayor o igual a {field_config['min']}"
                            )
                        if 'max' in field_config and float(value) > field_config['max']:
                            errors.setdefault(field_name, []).append(
                                f"El valor debe ser menor o igual a {field_config['max']}"
                            )
                    except (ValueError, TypeError):
                        errors.setdefault(field_name, []).append('Debe ser un número')
                
                elif field_config['type'] == 'select':
                    if 'options' in field_config:
                        valid_options = [opt['value'] if isinstance(opt, dict) else opt 
                                       for opt in field_config['options']]
                        if value not in valid_options:
                            errors.setdefault(field_name, []).append(
                                f"El valor debe ser uno de: {', '.join(str(o) for o in valid_options)}"
                            )
                
                elif field_config['type'] == 'date':
                    # Aquí podrías agregar validación de fecha si es necesario
                    pass
        
        return errors


class ProductCustomAttributes:
    """Helper para trabajar con atributos personalizados de productos"""
    
    def __init__(self, producto, company=None):
        self.producto = producto
        self.company = company
    
    def get_config(self) -> Dict[str, Any]:
        """Obtiene la configuración de campos personalizados de la empresa"""
        if not self.company:
            return {}
        return self.company.product_custom_fields_config or {}
    
    def get_attributes(self) -> Dict[str, Any]:
        """Obtiene todos los atributos personalizados del producto"""
        return self.producto.custom_attributes or {}
    
    def get_attribute(self, key: str, default=None) -> Any:
        """Obtiene un atributo personalizado específico"""
        return self.get_attributes().get(key, default)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Establece un atributo personalizado"""
        if not self.producto.custom_attributes:
            self.producto.custom_attributes = {}
        self.producto.custom_attributes[key] = value
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Establece múltiples atributos"""
        if not self.producto.custom_attributes:
            self.producto.custom_attributes = {}
        self.producto.custom_attributes.update(attributes)
    
    def validate(self) -> Dict[str, List[str]]:
        """Valida los atributos del producto contra su configuración"""
        config = self.get_config()
        if not config:
            return {}
        
        attributes = self.get_attributes()
        return CustomAttributeConfig.validate_values(config, attributes)
    
    def is_valid(self) -> bool:
        """Retorna True si los atributos son válidos"""
        return len(self.validate()) == 0
    
    def get_display_values(self) -> List[Dict[str, Any]]:
        """
        Retorna los atributos personalizados formateados para mostrar
        
        Ejemplo de retorno:
        [
            {'name': 'color', 'label': 'Color', 'value': 'Rojo'},
            {'name': 'garantia', 'label': 'Garantía (meses)', 'value': 12}
        ]
        """
        return self.build_display_values(self.get_config(), self.get_attributes())

    @staticmethod
    def build_display_values(config: Dict[str, Any], attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Construye valores listos para UI usando config + atributos."""
        if not config:
            # Fallback: mostrar claves tal cual si no hay configuración definida.
            return [
                {
                    'name': key,
                    'label': key.replace('_', ' ').title(),
                    'value': value,
                    'type': 'text',
                }
                for key, value in (attributes or {}).items()
            ]

        result = []
        for field_name, field_config in config.items():
            value = (attributes or {}).get(field_name)

            # Formatear valor según el tipo
            if field_config.get('type') == 'select' and 'options' in field_config:
                for option in field_config['options']:
                    if isinstance(option, dict):
                        if option.get('value') == value:
                            value = option.get('label', value)
                            break
                    elif option == value:
                        break

            result.append({
                'name': field_name,
                'label': field_config.get('label', field_name),
                'value': value,
                'type': field_config.get('type', 'text')
            })

        return result
