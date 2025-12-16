# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime, timedelta


class ProductTrendReport(models.Model):
    """Reporte de Tendencias de Productos - Análisis de Ventas"""
    _name = 'product.trend.report'
    _description = 'Reporte de Tendencias de Productos'
    _auto = False  # Vista SQL, no tabla física
    _order = 'total_revenue desc'

    # Dimensiones
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Plantilla Producto', readonly=True)
    categ_id = fields.Many2one('product.category', string='Categoría', readonly=True)
    
    # Período
    order_date = fields.Date(string='Fecha', readonly=True)
    year = fields.Char(string='Año', readonly=True)
    month = fields.Char(string='Mes', readonly=True)
    quarter = fields.Char(string='Trimestre', readonly=True)
    
    # Métricas de Ventas
    qty_sold = fields.Float(string='Cantidad Vendida', readonly=True, digits=(16, 2))
    total_revenue = fields.Float(string='Ingresos Totales', readonly=True, digits=(16, 2))
    avg_price = fields.Float(string='Precio Promedio', readonly=True, digits=(16, 2))
    order_count = fields.Integer(string='# Órdenes', readonly=True)
    
    # Cliente
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    user_id = fields.Many2one('res.users', string='Vendedor', readonly=True)
    team_id = fields.Many2one('crm.team', string='Equipo de Ventas', readonly=True)
    
    # Indicadores de Tendencia (calculados)
    trend_percentage = fields.Float(string='% Tendencia', compute='_compute_trend', store=False)
    trend_status = fields.Selection([
        ('hot', '🔥 Tendencia Alta'),
        ('rising', '📈 En Crecimiento'),
        ('stable', '➡️ Estable'),
        ('declining', '📉 En Declive'),
        ('cold', '❄️ Baja Demanda'),
    ], string='Estado de Tendencia', compute='_compute_trend', store=False)

    @api.depends('qty_sold', 'total_revenue')
    def _compute_trend(self):
        """Calcula el estado de tendencia basado en ventas recientes"""
        for record in self:
            # Comparar con promedio general del producto
            avg_sales = self.search([
                ('product_id', '=', record.product_id.id),
                ('order_date', '>=', fields.Date.today() - timedelta(days=90))
            ])
            
            if avg_sales:
                avg_qty = sum(avg_sales.mapped('qty_sold')) / len(avg_sales)
                if avg_qty > 0:
                    record.trend_percentage = ((record.qty_sold - avg_qty) / avg_qty) * 100
                    
                    # Clasificar tendencia
                    if record.trend_percentage >= 50:
                        record.trend_status = 'hot'
                    elif record.trend_percentage >= 20:
                        record.trend_status = 'rising'
                    elif record.trend_percentage >= -10:
                        record.trend_status = 'stable'
                    elif record.trend_percentage >= -30:
                        record.trend_status = 'declining'
                    else:
                        record.trend_status = 'cold'
                else:
                    record.trend_percentage = 0.0
                    record.trend_status = 'stable'
            else:
                record.trend_percentage = 0.0
                record.trend_status = 'stable'

    def init(self):
        """Inicializa la vista SQL del reporte"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Query SQL simplificada - PostgreSQL requiere todas las columnas en GROUP BY
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    MIN(sol.id) AS id,
                    sol.product_id,
                    MIN(pt.id) AS product_tmpl_id,
                    MIN(pt.categ_id) AS categ_id,
                    DATE(so.date_order) AS order_date,
                    TO_CHAR(so.date_order, 'YYYY') AS year,
                    TO_CHAR(so.date_order, 'YYYY-MM') AS month,
                    'Q' || TO_CHAR(so.date_order, 'Q') || ' ' || TO_CHAR(so.date_order, 'YYYY') AS quarter,
                    SUM(sol.product_uom_qty) AS qty_sold,
                    SUM(sol.price_subtotal) AS total_revenue,
                    AVG(sol.price_unit) AS avg_price,
                    COUNT(DISTINCT so.id) AS order_count,
                    so.partner_id,
                    so.user_id,
                    so.team_id
                FROM 
                    sale_order_line sol
                    INNER JOIN sale_order so ON sol.order_id = so.id
                    INNER JOIN product_product pp ON sol.product_id = pp.id
                    INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE 
                    so.state IN ('sale', 'done')
                GROUP BY 
                    sol.product_id,
                    DATE(so.date_order),
                    TO_CHAR(so.date_order, 'YYYY'),
                    TO_CHAR(so.date_order, 'YYYY-MM'),
                    TO_CHAR(so.date_order, 'Q'),
                    TO_CHAR(so.date_order, 'YYYY'),
                    so.partner_id,
                    so.user_id,
                    so.team_id
            )
        """ % self._table
        
        self.env.cr.execute(query)

    @api.model
    def get_top_trending_products(self, limit=10, days=30):
        """Obtiene los productos con mayor tendencia en los últimos días"""
        date_from = fields.Date.today() - timedelta(days=days)
        
        query = """
            SELECT 
                product_id,
                SUM(qty_sold) as total_qty,
                SUM(total_revenue) as total_rev,
                COUNT(*) as freq
            FROM %s
            WHERE order_date >= '%s'
            GROUP BY product_id
            ORDER BY total_rev DESC
            LIMIT %s
        """ % (self._table, date_from, limit)
        
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        
        trending_data = []
        for row in results:
            product = self.env['product.product'].browse(row['product_id'])
            trending_data.append({
                'product_name': product.name,
                'product_code': product.default_code or 'N/A',
                'qty_sold': row['total_qty'],
                'revenue': row['total_rev'],
                'frequency': row['freq'],
            })
        
        return trending_data

    @api.model
    def get_sales_forecast(self, product_id, months_ahead=3):
        """Proyección simple de ventas basada en promedio histórico"""
        historical = self.search([
            ('product_id', '=', product_id),
            ('order_date', '>=', fields.Date.today() - timedelta(days=180))
        ])
        
        if not historical:
            return {'forecast': 0, 'confidence': 'low'}
        
        avg_monthly_sales = sum(historical.mapped('qty_sold')) / 6  # 6 meses
        forecast = avg_monthly_sales * months_ahead
        
        # Calcular confianza basada en variabilidad
        qty_values = historical.mapped('qty_sold')
        if len(qty_values) > 1:
            import statistics
            std_dev = statistics.stdev(qty_values)
            cv = (std_dev / avg_monthly_sales) if avg_monthly_sales > 0 else 0
            
            if cv < 0.3:
                confidence = 'high'
            elif cv < 0.6:
                confidence = 'medium'
            else:
                confidence = 'low'
        else:
            confidence = 'low'
        
        return {
            'forecast_qty': round(forecast, 2),
            'avg_monthly': round(avg_monthly_sales, 2),
            'confidence': confidence,
            'months_ahead': months_ahead
        }
