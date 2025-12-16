# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime


class WhatsAppSalesTrendReport(models.Model):
    """Reporte de Tendencia de Ventas de Leads por WhatsApp"""
    _name = 'whatsapp.sales.trend.report'
    _description = 'Tendencia de Ventas - Leads WhatsApp'
    _auto = False
    _order = 'period_month desc, total_sales desc'

    # Asesor
    user_id = fields.Many2one('res.users', string='Asesor', readonly=True)
    team_id = fields.Many2one('crm.team', string='Equipo de Ventas', readonly=True)
    
    # Periodo
    period_month = fields.Char(string='Mes', readonly=True)
    period_year = fields.Char(string='Año', readonly=True)
    period_quarter = fields.Char(string='Trimestre', readonly=True)
    
    # Leads de WhatsApp
    total_leads = fields.Integer(string='# Leads WhatsApp', readonly=True)
    leads_won = fields.Integer(string='Leads Ganados', readonly=True)
    leads_lost = fields.Integer(string='Leads Perdidos', readonly=True)
    leads_active = fields.Integer(string='Leads Activos', readonly=True)
    
    # Conversión (almacenadas en SQL)
    conversion_rate = fields.Float(string='% Conversión', readonly=True, digits=(16, 2), aggregator='avg')
    win_rate = fields.Float(string='% Efectividad', readonly=True, digits=(16, 2), aggregator='avg')
    
    # Ventas Generadas
    total_sales = fields.Float(string='Ventas Generadas', readonly=True, digits=(16, 2), aggregator='sum')
    order_count = fields.Integer(string='# Órdenes', readonly=True, aggregator='sum')
    avg_deal_value = fields.Float(string='Valor Promedio Deal', readonly=True, digits=(16, 2), aggregator='avg')
    
    # Tiempo de Conversión
    avg_days_to_close = fields.Float(string='Días Promedio Cierre', readonly=True, digits=(16, 2))

    # @api.depends('total_leads', 'leads_won', 'total_sales', 'order_count', 'conversion_rate')
    # def _compute_metrics(self):
    #     """Método deshabilitado - los campos ahora se calculan en SQL"""
    #     pass

    def _old_compute_metrics(self):
        """Calcula métricas de desempeño"""
        for record in self:
            # Tasa de conversión
            if record.total_leads > 0:
                record.conversion_rate = (record.leads_won / record.total_leads) * 100
                closed_leads = record.leads_won + record.leads_lost
                if closed_leads > 0:
                    record.win_rate = (record.leads_won / closed_leads) * 100
                else:
                    record.win_rate = 0
            else:
                record.conversion_rate = 0
                record.win_rate = 0
            
            # Valor promedio del deal
            if record.leads_won > 0:
                record.avg_deal_value = record.total_sales / record.leads_won
            else:
                record.avg_deal_value = 0
            
            # Score de desempeño (fórmula ponderada)
            # 40% conversión + 30% ventas + 30% velocidad
            conversion_score = min(record.conversion_rate / 50 * 40, 40)  # Max 40 pts
            sales_score = min(record.total_sales / 500000 * 30, 30)  # Max 30 pts
            speed_score = 0
            if record.avg_days_to_close > 0:
                speed_score = max(30 - (record.avg_days_to_close / 30 * 30), 0)  # Max 30 pts
            
            record.performance_score = conversion_score + sales_score + speed_score
            
            # Estado de desempeño
            if record.performance_score >= 75:
                record.performance_status = 'excellent'
            elif record.performance_score >= 60:
                record.performance_status = 'good'
            elif record.performance_score >= 40:
                record.performance_status = 'average'
            else:
                record.performance_status = 'poor'

    def init(self):
        """Crea la vista SQL del reporte"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY period_month, user_id) AS id,
                    user_id,
                    team_id,
                    period_month,
                    period_year,
                    period_quarter,
                    total_leads,
                    leads_won,
                    leads_lost,
                    leads_active,
                    COALESCE(total_sales, 0) AS total_sales,
                    COALESCE(order_count, 0) AS order_count,
                    COALESCE(conversion_rate, 0) AS conversion_rate,
                    COALESCE(win_rate, 0) AS win_rate,
                    COALESCE(avg_deal_value, 0) AS avg_deal_value,
                    COALESCE(avg_days_to_close, 0) AS avg_days_to_close
                FROM (
                    SELECT 
                        cl.user_id,
                        cl.team_id,
                        TO_CHAR(cl.create_date, 'YYYY-MM') AS period_month,
                        TO_CHAR(cl.create_date, 'YYYY') AS period_year,
                        'Q' || TO_CHAR(cl.create_date, 'Q') || ' ' || TO_CHAR(cl.create_date, 'YYYY') AS period_quarter,
                        COUNT(DISTINCT cl.id) AS total_leads,
                        COUNT(DISTINCT CASE 
                            WHEN cs.is_won = true THEN cl.id 
                        END) AS leads_won,
                        COUNT(DISTINCT CASE 
                            WHEN cs.is_won = false AND cl.active = false THEN cl.id 
                        END) AS leads_lost,
                        COUNT(DISTINCT CASE 
                            WHEN cl.active = true THEN cl.id 
                        END) AS leads_active,
                        SUM(COALESCE(sales.total_amount, 0)) AS total_sales,
                        COUNT(DISTINCT sales.order_id) AS order_count,
                        CASE 
                            WHEN COUNT(DISTINCT cl.id) > 0 
                            THEN (COUNT(DISTINCT CASE WHEN cs.is_won = true THEN cl.id END)::float / COUNT(DISTINCT cl.id)) * 100 
                            ELSE 0 
                        END AS conversion_rate,
                        CASE 
                            WHEN (COUNT(DISTINCT CASE WHEN cs.is_won = true THEN cl.id END) + COUNT(DISTINCT CASE WHEN cs.is_won = false AND cl.active = false THEN cl.id END)) > 0 
                            THEN (COUNT(DISTINCT CASE WHEN cs.is_won = true THEN cl.id END)::float / (COUNT(DISTINCT CASE WHEN cs.is_won = true THEN cl.id END) + COUNT(DISTINCT CASE WHEN cs.is_won = false AND cl.active = false THEN cl.id END))) * 100 
                            ELSE 0 
                        END AS win_rate,
                        CASE 
                            WHEN COUNT(DISTINCT sales.order_id) > 0 
                            THEN SUM(COALESCE(sales.total_amount, 0)) / COUNT(DISTINCT sales.order_id) 
                            ELSE 0 
                        END AS avg_deal_value,
                        AVG(CASE 
                            WHEN cl.date_closed IS NOT NULL 
                            THEN EXTRACT(EPOCH FROM (cl.date_closed - cl.create_date)) / 86400 
                        END) AS avg_days_to_close
                    FROM crm_lead cl
                    LEFT JOIN crm_stage cs ON cs.id = cl.stage_id
                    LEFT JOIN (
                        SELECT 
                            so.opportunity_id,
                            so.id AS order_id,
                            so.amount_total AS total_amount
                        FROM sale_order so
                        WHERE so.state IN ('sale', 'done')
                    ) sales ON sales.opportunity_id = cl.id
                    WHERE 
                        cl.user_id IS NOT NULL
                        AND (
                            LOWER(cl.name) LIKE '%%whatsapp%%'
                            OR LOWER(COALESCE(cl.description, '')) LIKE '%%whatsapp%%'
                            OR EXISTS (
                                SELECT 1 FROM mail_message mm 
                                WHERE mm.res_id = cl.id 
                                AND mm.model = 'crm.lead'
                                AND LOWER(mm.body) LIKE '%%whatsapp%%'
                            )
                        )
                    GROUP BY 
                        cl.user_id,
                        cl.team_id,
                        TO_CHAR(cl.create_date, 'YYYY-MM'),
                        TO_CHAR(cl.create_date, 'YYYY'),
                        'Q' || TO_CHAR(cl.create_date, 'Q') || ' ' || TO_CHAR(cl.create_date, 'YYYY')
                ) subquery
            )
        """ % self._table
        
        self.env.cr.execute(query)

    def action_view_leads(self):
        """Abre los leads de WhatsApp del periodo y asesor"""
        self.ensure_one()
        
        # Parsear el periodo
        year, month = self.period_month.split('-')
        
        return {
            'name': f'Leads WhatsApp - {self.user_id.name} ({self.period_month})',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'list,kanban,form',
            'domain': [
                ('user_id', '=', self.user_id.id),
                ('create_date', '>=', f'{year}-{month}-01'),
                ('create_date', '<', f'{year}-{int(month)+1:02d}-01' if int(month) < 12 else f'{int(year)+1}-01-01'),
                '|', '|',
                ('name', 'ilike', 'whatsapp'),
                ('description', 'ilike', 'whatsapp'),
                ('message_ids.body', 'ilike', 'whatsapp'),
            ],
            'context': {'create': False},
        }

    @api.model
    def get_advisor_comparison(self, period=None):
        """Compara el desempeño de todos los asesores"""
        domain = []
        if period:
            domain.append(('period_month', '=', period))
        
        advisors = self.search(domain, order='performance_score desc')
        
        return [{
            'advisor': adv.user_id.name,
            'leads': adv.total_leads,
            'won': adv.leads_won,
            'conversion': adv.conversion_rate,
            'sales': adv.total_sales,
            'score': adv.performance_score,
        } for adv in advisors]

    @api.model
    def get_monthly_trend(self, user_id, months=6):
        """Obtiene la tendencia mensual de un asesor"""
        records = self.search([
            ('user_id', '=', user_id)
        ], order='period_month desc', limit=months)
        
        return [{
            'month': r.period_month,
            'leads': r.total_leads,
            'won': r.leads_won,
            'conversion': r.conversion_rate,
            'sales': r.total_sales,
        } for r in reversed(records)]
