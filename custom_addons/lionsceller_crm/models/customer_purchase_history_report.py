# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime, timedelta


class CustomerPurchaseHistoryReport(models.Model):
    """Reporte Histórico de Compras por Cliente"""
    _name = 'customer.purchase.history.report'
    _description = 'Historial de Compras de Clientes'
    _auto = False
    _order = 'total_purchased desc'

    # Cliente
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    partner_name = fields.Char(string='Nombre del Cliente', readonly=True)
    partner_email = fields.Char(string='Email', readonly=True)
    partner_phone = fields.Char(string='Teléfono', readonly=True)
    partner_city = fields.Char(string='Ciudad', readonly=True)
    
    # Ventas Totales
    total_purchased = fields.Float(string='Total Comprado', readonly=True, digits=(16, 2))
    order_count = fields.Integer(string='# Órdenes', readonly=True)
    product_count = fields.Integer(string='# Productos Diferentes', readonly=True)
    total_qty = fields.Float(string='Cantidad Total', readonly=True, digits=(16, 2))
    
    # Análisis Temporal
    first_purchase_date = fields.Date(string='Primera Compra', readonly=True)
    last_purchase_date = fields.Date(string='Última Compra', readonly=True)
    
    # Métricas Calculadas (almacenadas en SQL)
    avg_order_value = fields.Float(string='Ticket Promedio', readonly=True, digits=(16, 2), aggregator='avg')
    purchase_frequency_days = fields.Float(string='Frecuencia de Compra (días)', readonly=True, digits=(16, 2), aggregator='avg')
    
    # Top Productos
    top_product_id = fields.Many2one('product.product', string='Producto Más Comprado', readonly=True)
    top_product_qty = fields.Float(string='Cantidad del Top Producto', readonly=True, digits=(16, 2))
    
    # Vendedor Asignado
    user_id = fields.Many2one('res.users', string='Vendedor', readonly=True)
    team_id = fields.Many2one('crm.team', string='Equipo de Ventas', readonly=True)

    # @api.depends('total_purchased', 'order_count', 'last_purchase_date', 'first_purchase_date')
    # def _compute_purchase_metrics(self):
    #     """Calcula métricas de comportamiento de compra"""
    #     # Método deshabilitado - los campos ahora se calculan en SQL
    #     pass

    def init(self):
        """Crea la vista SQL del reporte"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY partner_id) AS id,
                    partner_id,
                    partner_name,
                    partner_email,
                    partner_phone,
                    partner_city,
                    total_purchased,
                    order_count,
                    product_count,
                    total_qty,
                    first_purchase_date,
                    last_purchase_date,
                    avg_order_value,
                    purchase_frequency_days,
                    top_product_id,
                    top_product_qty,
                    user_id,
                    team_id
                FROM (
                    SELECT 
                        so.partner_id,
                        rp.name AS partner_name,
                        rp.email AS partner_email,
                        rp.phone AS partner_phone,
                        rp.city AS partner_city,
                        SUM(so.amount_total) AS total_purchased,
                        COUNT(DISTINCT so.id) AS order_count,
                        COUNT(DISTINCT sol.product_id) AS product_count,
                        SUM(sol.product_uom_qty) AS total_qty,
                        MIN(so.date_order::date) AS first_purchase_date,
                        MAX(so.date_order::date) AS last_purchase_date,
                        CASE 
                            WHEN COUNT(DISTINCT so.id) > 0 
                            THEN SUM(so.amount_total) / COUNT(DISTINCT so.id) 
                            ELSE 0 
                        END AS avg_order_value,
                        CASE 
                            WHEN COUNT(DISTINCT so.id) > 1 
                            THEN EXTRACT(EPOCH FROM (MAX(so.date_order) - MIN(so.date_order))) / 86400.0 / (COUNT(DISTINCT so.id) - 1) 
                            ELSE 0 
                        END AS purchase_frequency_days,
                        top_products.product_id AS top_product_id,
                        top_products.total_qty AS top_product_qty,
                        so.user_id,
                        so.team_id
                    FROM sale_order so
                    INNER JOIN res_partner rp ON rp.id = so.partner_id
                    LEFT JOIN sale_order_line sol ON sol.order_id = so.id
                    LEFT JOIN LATERAL (
                        SELECT 
                            sol2.product_id,
                            SUM(sol2.product_uom_qty) AS total_qty
                        FROM sale_order_line sol2
                        INNER JOIN sale_order so2 ON so2.id = sol2.order_id
                        WHERE so2.partner_id = so.partner_id
                            AND so2.state IN ('sale', 'done')
                            AND sol2.product_id IS NOT NULL
                        GROUP BY sol2.product_id
                        ORDER BY SUM(sol2.product_uom_qty) DESC
                        LIMIT 1
                    ) top_products ON true
                    WHERE 
                        so.state IN ('sale', 'done')
                    GROUP BY 
                        so.partner_id,
                        rp.name,
                        rp.email,
                        rp.phone,
                        rp.city,
                        top_products.product_id,
                        top_products.total_qty,
                        so.user_id,
                        so.team_id
                ) subquery
            )
        """ % self._table
        
        self.env.cr.execute(query)

    def action_view_customer_orders(self):
        """Abre las órdenes de venta del cliente"""
        self.ensure_one()
        return {
            'name': f'Órdenes de {self.partner_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id), ('state', 'in', ['sale', 'done'])],
            'context': {'create': False},
        }

    def action_view_customer_products(self):
        """Muestra los productos comprados por el cliente"""
        self.ensure_one()
        
        # Obtener productos comprados
        product_ids = self.env['sale.order.line'].search([
            ('order_id.partner_id', '=', self.partner_id.id),
            ('order_id.state', 'in', ['sale', 'done']),
        ]).mapped('product_id').ids
        
        return {
            'name': f'Productos Comprados por {self.partner_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', product_ids)],
            'context': {'create': False},
        }

    @api.model
    def get_customer_timeline(self, partner_id):
        """Obtiene la línea de tiempo de compras del cliente"""
        orders = self.env['sale.order'].search([
            ('partner_id', '=', partner_id),
            ('state', 'in', ['sale', 'done'])
        ], order='date_order desc')
        
        timeline = []
        for order in orders:
            timeline.append({
                'date': order.date_order.strftime('%Y-%m-%d'),
                'order_name': order.name,
                'amount': order.amount_total,
                'products_count': len(order.order_line),
                'state': order.state,
            })
        
        return timeline

    @api.model
    def get_top_customers(self, limit=10, period_months=None):
        """Obtiene los mejores clientes"""
        domain = []
        if period_months:
            date_from = datetime.now() - timedelta(days=period_months * 30)
            domain.append(('last_purchase_date', '>=', date_from.date()))
        
        return self.search(domain, order='total_purchased desc', limit=limit)
