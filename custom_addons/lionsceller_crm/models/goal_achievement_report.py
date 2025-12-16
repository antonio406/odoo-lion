# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime, timedelta


class GoalAchievementReport(models.Model):
    """Reporte de Cumplimiento de Metas de Ventas"""
    _name = 'goal.achievement.report'
    _description = 'Reporte de Cumplimiento de Metas'
    _auto = False
    _order = 'period_month desc, total_sales desc'

    # Dimensiones
    user_id = fields.Many2one('res.users', string='Vendedor', readonly=True)
    team_id = fields.Many2one('crm.team', string='Equipo de Ventas', readonly=True)
    period_month = fields.Char(string='Mes', readonly=True)
    period_year = fields.Char(string='Año', readonly=True)
    
    # Métricas de Ventas
    total_sales = fields.Float(string='Ventas Realizadas', readonly=True, digits=(16, 2))
    order_count = fields.Integer(string='# Órdenes', readonly=True)
    won_opportunities = fields.Integer(string='Oportunidades Ganadas', readonly=True)
    
    # Metas
    sales_goal = fields.Float(string='Meta de Ventas', readonly=True, digits=(16, 2))
    opportunity_goal = fields.Integer(string='Meta Oportunidades', readonly=True)
    
    # Cumplimiento
    achievement_percentage = fields.Float(string='% Cumplimiento', compute='_compute_achievement', store=False, aggregator='avg')
    achievement_status = fields.Selection([
        ('exceeded', '🏆 Superado'),
        ('achieved', '✅ Alcanzado'),
        ('in_progress', '📊 En Progreso'),
        ('at_risk', '⚠️ En Riesgo'),
        ('not_achieved', '❌ No Alcanzado'),
    ], string='Estado', compute='_compute_achievement', store=False)
    
    remaining_amount = fields.Float(string='Faltante', compute='_compute_achievement', store=False, digits=(16, 2))
    days_remaining = fields.Integer(string='Días Restantes', compute='_compute_days_remaining', store=False)

    @api.depends('total_sales', 'sales_goal')
    def _compute_achievement(self):
        """Calcula el porcentaje de cumplimiento y estado"""
        for record in self:
            if record.sales_goal > 0:
                record.achievement_percentage = (record.total_sales / record.sales_goal) * 100
                record.remaining_amount = record.sales_goal - record.total_sales
                
                # Determinar estado basado en porcentaje
                if record.achievement_percentage >= 100:
                    record.achievement_status = 'exceeded' if record.achievement_percentage > 110 else 'achieved'
                elif record.achievement_percentage >= 80:
                    record.achievement_status = 'in_progress'
                elif record.achievement_percentage >= 50:
                    record.achievement_status = 'at_risk'
                else:
                    record.achievement_status = 'not_achieved'
            else:
                record.achievement_percentage = 0
                record.remaining_amount = 0
                record.achievement_status = 'not_achieved'

    @api.depends('period_month', 'period_year')
    def _compute_days_remaining(self):
        """Calcula días restantes del mes"""
        for record in self:
            try:
                if record.period_month and record.period_year:
                    year, month = int(record.period_year), int(record.period_month.split('-')[1])
                    # Último día del mes
                    if month == 12:
                        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
                    
                    today = datetime.now()
                    if last_day.date() >= today.date():
                        record.days_remaining = (last_day.date() - today.date()).days
                    else:
                        record.days_remaining = 0
                else:
                    record.days_remaining = 0
            except:
                record.days_remaining = 0

    def init(self):
        """Crea la vista SQL del reporte"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY user_id, period_month) AS id,
                    user_id,
                    team_id,
                    period_month,
                    period_year,
                    total_sales,
                    order_count,
                    won_opportunities,
                    COALESCE(sales_goal, 1000000) AS sales_goal,
                    COALESCE(opportunity_goal, 10) AS opportunity_goal
                FROM (
                    SELECT 
                        so.user_id,
                        so.team_id,
                        TO_CHAR(so.date_order, 'YYYY-MM') AS period_month,
                        TO_CHAR(so.date_order, 'YYYY') AS period_year,
                        SUM(so.amount_total) AS total_sales,
                        COUNT(DISTINCT so.id) AS order_count,
                        COALESCE(opp.won_count, 0) AS won_opportunities,
                        500000.00 AS sales_goal,
                        5 AS opportunity_goal
                    FROM sale_order so
                    LEFT JOIN (
                        SELECT 
                            user_id,
                            TO_CHAR(date_closed, 'YYYY-MM') AS period_month,
                            COUNT(*) AS won_count
                        FROM crm_lead
                        WHERE stage_id IN (
                            SELECT id FROM crm_stage WHERE is_won = true
                        )
                        GROUP BY user_id, TO_CHAR(date_closed, 'YYYY-MM')
                    ) opp ON opp.user_id = so.user_id AND opp.period_month = TO_CHAR(so.date_order, 'YYYY-MM')
                    WHERE 
                        so.state IN ('sale', 'done')
                        AND so.user_id IS NOT NULL
                    GROUP BY 
                        so.user_id,
                        so.team_id,
                        TO_CHAR(so.date_order, 'YYYY-MM'),
                        TO_CHAR(so.date_order, 'YYYY'),
                        opp.won_count
                ) subquery
            )
        """ % self._table
        
        self.env.cr.execute(query)

    @api.model
    def get_team_performance(self, team_id=None, period=None):
        """Obtiene el desempeño del equipo"""
        domain = []
        if team_id:
            domain.append(('team_id', '=', team_id))
        if period:
            domain.append(('period_month', '=', period))
        
        records = self.search(domain)
        
        total_sales = sum(records.mapped('total_sales'))
        total_goal = sum(records.mapped('sales_goal'))
        
        return {
            'total_sales': total_sales,
            'total_goal': total_goal,
            'achievement_percentage': (total_sales / total_goal * 100) if total_goal > 0 else 0,
            'salespeople_count': len(records),
            'top_performers': records.sorted(lambda r: r.achievement_percentage, reverse=True)[:3],
        }

    @api.model
    def get_monthly_trend(self, user_id, months=6):
        """Obtiene la tendencia mensual de un vendedor"""
        records = self.search([
            ('user_id', '=', user_id)
        ], order='period_month desc', limit=months)
        
        return [{
            'month': r.period_month,
            'sales': r.total_sales,
            'goal': r.sales_goal,
            'achievement': r.achievement_percentage,
        } for r in reversed(records)]
