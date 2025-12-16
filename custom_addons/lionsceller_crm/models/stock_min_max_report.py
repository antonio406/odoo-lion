# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime, timedelta


class StockMinMaxReport(models.Model):
    """Reporte de Inventarios Mínimos y Máximos"""
    _name = 'stock.minmax.report'
    _description = 'Reporte de Inventarios Mínimos y Máximos'
    _auto = False
    _order = 'qty_available asc, product_id'

    # Información del Producto
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Plantilla', readonly=True)
    categ_id = fields.Many2one('product.category', string='Categoría', readonly=True)
    default_code = fields.Char(string='Referencia Interna', readonly=True)
    
    # Inventario Actual
    qty_available = fields.Float(string='Stock Disponible', readonly=True, digits=(16, 2))
    virtual_available = fields.Float(string='Stock Previsto', readonly=True, digits=(16, 2))
    
    # Consumo y Rotación (últimos 90 días)
    avg_daily_consumption = fields.Float(string='Consumo Diario Promedio', readonly=True, digits=(16, 2))
    total_consumption_90d = fields.Float(string='Consumo Total (90 días)', readonly=True, digits=(16, 2))
    days_of_stock = fields.Float(string='Días de Stock', compute='_compute_stock_metrics', store=False, aggregator='avg')
    
    # Inventarios Calculados
    min_stock = fields.Float(string='Stock Mínimo', compute='_compute_min_max', store=False, digits=(16, 2), aggregator='sum')
    max_stock = fields.Float(string='Stock Máximo', compute='_compute_min_max', store=False, digits=(16, 2), aggregator='sum')
    reorder_point = fields.Float(string='Punto de Reorden', compute='_compute_min_max', store=False, digits=(16, 2), aggregator='sum')
    
    # Alertas y Recomendaciones
    stock_status = fields.Selection([
        ('overstock', '📦 Sobrestock'),
        ('optimal', '✅ Óptimo'),
        ('reorder', '⚠️ Punto de Reorden'),
        ('low', '🔴 Stock Bajo'),
        ('critical', '🚨 Crítico'),
        ('stockout', '❌ Sin Stock'),
    ], string='Estado', compute='_compute_stock_metrics', store=False)
    
    alert_level = fields.Integer(string='Nivel de Alerta', compute='_compute_stock_metrics', store=False)
    qty_to_order = fields.Float(string='Cantidad a Ordenar', compute='_compute_stock_metrics', store=False, digits=(16, 2), aggregator='sum')
    
    # Costos
    standard_price = fields.Float(string='Costo Unitario', readonly=True, digits=(16, 2))
    stock_value = fields.Float(string='Valor en Stock', compute='_compute_stock_metrics', store=False, digits=(16, 2), aggregator='sum')

    @api.depends('qty_available', 'avg_daily_consumption', 'standard_price')
    def _compute_stock_metrics(self):
        """Calcula métricas de stock y alertas"""
        for record in self:
            # Días de stock disponible
            if record.avg_daily_consumption > 0:
                record.days_of_stock = record.qty_available / record.avg_daily_consumption
            else:
                record.days_of_stock = 999  # Sin consumo = infinito
            
            # Valor del inventario
            record.stock_value = record.qty_available * record.standard_price
            
            # Determinar estado y nivel de alerta
            min_stock = record.min_stock
            max_stock = record.max_stock
            reorder = record.reorder_point
            
            if record.qty_available <= 0:
                record.stock_status = 'stockout'
                record.alert_level = 5
                record.qty_to_order = max_stock
            elif record.qty_available < min_stock:
                record.stock_status = 'critical'
                record.alert_level = 4
                record.qty_to_order = max_stock - record.qty_available
            elif record.qty_available < reorder:
                record.stock_status = 'low'
                record.alert_level = 3
                record.qty_to_order = max_stock - record.qty_available
            elif record.qty_available <= reorder:
                record.stock_status = 'reorder'
                record.alert_level = 2
                record.qty_to_order = max_stock - record.qty_available
            elif record.qty_available > max_stock:
                record.stock_status = 'overstock'
                record.alert_level = 1
                record.qty_to_order = 0
            else:
                record.stock_status = 'optimal'
                record.alert_level = 0
                record.qty_to_order = 0

    @api.depends('avg_daily_consumption')
    def _compute_min_max(self):
        """Calcula inventarios mínimos y máximos basados en consumo"""
        for record in self:
            # Parámetros configurables
            lead_time_days = 7  # Tiempo de reabastecimiento
            safety_stock_days = 3  # Stock de seguridad
            service_level_days = 30  # Nivel de servicio (1 mes)
            
            daily_consumption = record.avg_daily_consumption or 0
            
            # Stock Mínimo = (Consumo diario × Lead time) + Stock de seguridad
            record.min_stock = (daily_consumption * lead_time_days) + (daily_consumption * safety_stock_days)
            
            # Punto de Reorden = Stock Mínimo + (Consumo durante lead time)
            record.reorder_point = record.min_stock + (daily_consumption * lead_time_days * 0.5)
            
            # Stock Máximo = Consumo diario × Nivel de servicio
            record.max_stock = daily_consumption * service_level_days
            
            # Si no hay consumo, establecer valores por defecto bajos
            if daily_consumption == 0:
                record.min_stock = 10
                record.reorder_point = 15
                record.max_stock = 30

    def init(self):
        """Crea la vista SQL del reporte"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    pp.id AS id,
                    pp.id AS product_id,
                    pt.id AS product_tmpl_id,
                    pt.categ_id,
                    pp.default_code,
                    COALESCE(stock.qty_available, 0) AS qty_available,
                    COALESCE(stock.virtual_available, 0) AS virtual_available,
                    COALESCE(consumption.total_qty / 90.0, 0) AS avg_daily_consumption,
                    COALESCE(consumption.total_qty, 0) AS total_consumption_90d,
                    0.0 AS standard_price
                FROM 
                    product_product pp
                    INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN (
                        -- Stock actual del producto
                        SELECT 
                            product_id,
                            SUM(quantity) AS qty_available,
                            SUM(quantity) AS virtual_available
                        FROM stock_quant
                        WHERE location_id IN (
                            SELECT id FROM stock_location 
                            WHERE usage = 'internal'
                        )
                        GROUP BY product_id
                    ) stock ON stock.product_id = pp.id
                    LEFT JOIN (
                        -- Consumo en los últimos 90 días
                        SELECT 
                            sol.product_id,
                            SUM(sol.product_uom_qty) AS total_qty
                        FROM sale_order_line sol
                        INNER JOIN sale_order so ON sol.order_id = so.id
                        WHERE 
                            so.state IN ('sale', 'done')
                            AND so.date_order >= CURRENT_DATE - INTERVAL '90 days'
                        GROUP BY sol.product_id
                    ) consumption ON consumption.product_id = pp.id
                WHERE 
                    pt.active = true
                    AND pt.type IN ('product', 'consu')
            )
        """ % self._table
        
        self.env.cr.execute(query)

    @api.model
    def get_critical_products(self, limit=20):
        """Obtiene productos en estado crítico o sin stock"""
        return self.search([], order='alert_level desc, qty_available asc', limit=limit)

    @api.model
    def get_reorder_suggestions(self):
        """Genera sugerencias de reorden para productos bajo punto de reorden"""
        products = self.search([])
        suggestions = []
        
        for product in products:
            if product.qty_to_order > 0 and product.alert_level >= 2:
                suggestions.append({
                    'product_id': product.product_id.id,
                    'product_name': product.product_id.name,
                    'current_stock': product.qty_available,
                    'min_stock': product.min_stock,
                    'max_stock': product.max_stock,
                    'qty_to_order': product.qty_to_order,
                    'estimated_cost': product.qty_to_order * product.standard_price,
                    'alert_level': product.stock_status,
                })
        
        return sorted(suggestions, key=lambda x: x['alert_level'], reverse=True)

    @api.model
    def get_stock_summary(self):
        """Resumen general del estado de inventarios"""
        all_products = self.search([])
        
        total_products = len(all_products)
        critical = len([p for p in all_products if p.alert_level >= 4])
        low = len([p for p in all_products if p.alert_level == 3])
        reorder = len([p for p in all_products if p.alert_level == 2])
        overstock = len([p for p in all_products if p.stock_status == 'overstock'])
        optimal = len([p for p in all_products if p.stock_status == 'optimal'])
        
        total_value = sum(p.stock_value for p in all_products)
        
        return {
            'total_products': total_products,
            'critical': critical,
            'low': low,
            'reorder': reorder,
            'overstock': overstock,
            'optimal': optimal,
            'total_inventory_value': total_value,
        }
