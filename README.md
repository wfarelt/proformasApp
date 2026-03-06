# proformasApp

## Descripción

**proformasApp** es un sistema integral de gestión empresarial desarrollado en Django que permite administrar proformas, inventario, compras y clientes de manera eficiente. Diseñado como una solución multi-empresa (SaaS), cada compañía puede personalizar productos con atributos específicos según sus necesidades sin requerir cambios en el código.

### Funcionalidades Principales

- **Gestión de Proformas**: Creación, edición y seguimiento de cotizaciones con estados (pendiente, ejecutado, anulado)
- **Inventario Inteligente**: Control de stock con movimientos de entrada/salida automáticos vinculados a compras y ventas
- **Módulo de Compras**: Registro de compras a proveedores con actualización automática de inventario y precios
- **Atributos Personalizables**: Campos dinámicos por empresa para productos (color, talla, voltaje, etc.) sin migraciones de base de datos
- **Kits de Productos**: Agrupación de productos para ventas combinadas
- **Multi-Empresa**: Soporte para múltiples compañías con datos aislados y configuraciones independientes
- **Reportes y Análisis**: Productos más vendidos, historial de ventas, reportes de proformas por período
- **Gestión de Precios**: Sistema de aprobación para cambios de precios con historial completo
- **Exportación PDF**: Generación de documentos profesionales para proformas y movimientos de inventario
- **Panel Administrativo**: Interfaz intuitiva con Bootstrap AdminLTE para gestión completa

### Tecnologías

- **Backend**: Django 5.0.6, Python
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: Bootstrap 4, AdminLTE, jQuery
- **PDFs**: WeasyPrint
- **Autenticación**: Sistema personalizado con perfiles de usuario por empresa

### Módulos

- `core`: Productos, clientes, proformas, usuarios, empresas, marcas, kits
- `inv`: Inventario, compras, proveedores, movimientos de stock, reportes

