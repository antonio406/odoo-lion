# 📊 Reporte de Tendencias de Productos

## Descripción

El **Reporte de Tendencias de Productos** es un módulo de análisis avanzado que calcula métricas clave de ventas para Lionsceller. Analiza las órdenes de venta confirmadas y genera insights sobre el desempeño de productos.

## 🎯 Características

### Métricas Calculadas

- **Cantidad Vendida**: Total de unidades vendidas por producto
- **Ingresos Totales**: Suma de ventas por producto
- **Precio Promedio**: Precio promedio de venta
- **# Órdenes**: Número de órdenes que incluyen el producto

### Dimensiones de Análisis

- Producto individual
- Categoría de producto
- Período (Día, Mes, Trimestre, Año)
- Cliente
- Vendedor
- Equipo de ventas

## 🚀 Uso

### Acceder al Reporte

1. Ve a **CRM → Reportes → Tendencias de Productos**
2. O usa la URL directa: `http://localhost:8069/web#action=lionsceller_crm.action_product_trend_report`

### Vistas Disponibles

#### 📈 Vista de Gráfico (Por Defecto)
- Muestra tendencias de ventas en el tiempo
- Gráfico de líneas por mes
- Ideal para ver evolución temporal

#### 📊 Vista Pivot
- Tabla dinámica para análisis multidimensional
- Arrastra y suelta dimensiones
- Agrupa por categoría, mes, vendedor, etc.

#### 📋 Vista de Lista
- Listado detallado de todas las transacciones
- Totales automáticos
- Exportable a Excel

#### 📱 Vista Kanban
- Vista tipo tarjetas para dispositivos móviles
- Información resumida por producto

## 🔍 Filtros Disponibles

### Filtros de Fecha
- **Este Mes**: Últimos 30 días
- **Este Trimestre**: Últimos 90 días  
- **Este Año**: Año actual

### Agrupaciones
- Por Producto
- Por Categoría
- Por Mes/Trimestre/Año
- Por Vendedor
- Por Cliente

## 🛠️ Funciones Avanzadas (Python API)

### Obtener Top Productos
```python
# Top 10 productos de los últimos 30 días
trending = env['product.trend.report'].get_top_trending_products(limit=10, days=30)
```

### Proyección de Ventas
```python
# Proyectar ventas para 3 meses
forecast = env['product.trend.report'].get_sales_forecast(product_id=123, months_ahead=3)
# Retorna: {'forecast_qty': 150, 'avg_monthly': 50, 'confidence': 'high'}
```

## 📝 Datos de Ejemplo

Para generar datos de ejemplo y probar el reporte:

```bash
python simular_ventas.py
```

Este script:
- ✅ Crea 30 órdenes de venta simuladas
- ✅ Distribuye ventas en los últimos 6 meses
- ✅ Asigna productos y cantidades aleatorias
- ✅ Confirma las órdenes automáticamente

## 🎨 Interpretación de Datos

### Análisis de Tendencias

El campo `trend_status` (calculado) clasifica productos en:

- 🔥 **Tendencia Alta**: +50% sobre promedio
- 📈 **En Crecimiento**: +20% a +50%
- ➡️ **Estable**: -10% a +20%
- 📉 **En Declive**: -30% a -10%
- ❄️ **Baja Demanda**: Menos de -30%

### Casos de Uso

1. **Identificar best-sellers**: Productos con mayor revenue total
2. **Análisis estacional**: Comparar ventas por trimestre
3. **Performance de vendedores**: Agrupar por usuario
4. **Comportamiento de clientes**: Ver qué productos compran más
5. **Planificación de inventario**: Usar proyecciones para reabastecimiento

## ⚙️ Requisitos Técnicos

### Dependencias
- Módulo `sale` (Ventas)
- Módulo `product` (Productos)
- Módulo `crm` (CRM)

### Base de Datos
El reporte utiliza una **vista SQL materializada** que se actualiza automáticamente con cada venta confirmada.

### Permisos
- **Vendedores** (`sales_team.group_sale_salesman`): Lectura
- **Gerentes** (`sales_team.group_sale_manager`): Lectura

## 🐛 Solución de Problemas

### No aparecen datos
1. Verifica que existan órdenes de venta **confirmadas** (estado: `sale` o `done`)
2. Ejecuta `simular_ventas.py` para crear datos de ejemplo
3. Revisa que los productos tengan ventas asociadas

### Error al cargar vista
1. Actualiza el módulo: `python odoo-bin -c odoo.conf -d lion-sceller -u lionsceller_crm --stop-after-init`
2. Reinicia Odoo

### Fechas incorrectas
El reporte usa la fecha de la orden (`date_order`), no la fecha de entrega.

## 📚 Estructura de Archivos

```
addons/lionsceller_crm/
├── models/
│   └── product_trend_report.py    # Modelo del reporte
├── views/
│   └── product_trend_report_views.xml  # Vistas y menú
└── security/
    └── ir.model.access.csv        # Permisos de acceso
```

## 🔄 Actualización del Módulo

```bash
python odoo-bin -c odoo.conf -d lion-sceller -u lionsceller_crm --stop-after-init
```

## 💡 Tips de Uso

1. **Usa la vista Pivot** para análisis exploratorio rápido
2. **Exporta a Excel** desde la vista de lista para análisis offline
3. **Combina filtros** de fecha con agrupaciones para insights específicos
4. **Guarda filtros personalizados** usando "Favoritos" en la búsqueda
5. **Compara períodos** usando filtros de mes/trimestre

---

**Desarrollado para Lionsceller CRM**  
Versión: 1.0  
Compatible con: Odoo 18.0
