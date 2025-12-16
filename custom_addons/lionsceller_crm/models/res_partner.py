# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Al crear un contacto/cliente, automáticamente:
        1. Asigna el primer asesor de ventas disponible si no tiene uno
        2. Crea una oportunidad automáticamente
        """
        partners = super(Partner, self).create(vals_list)
        
        for partner in partners:
            _logger.info(f"Partner creado: {partner.name}, user_id: {partner.user_id}, parent_id: {partner.parent_id}")
            
            # Solo procesar si no es un contacto hijo de una empresa
            if not partner.parent_id:
                # Si no tiene asesor asignado, asignar el primero disponible
                if not partner.user_id:
                    # Buscar el primer usuario con permisos de ventas
                    salesperson = self.env['res.users'].search([
                        ('share', '=', False),  # No es usuario portal
                        ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id)
                    ], limit=1)
                    
                    if salesperson:
                        partner.user_id = salesperson.id
                        _logger.info(f"Asesor asignado automáticamente: {salesperson.name} a {partner.name}")
                
                # Crear oportunidad si tiene asesor (asignado manual o automáticamente)
                if partner.user_id:
                    _logger.info(f"Creando oportunidad automática para {partner.name}")
                    
                    # Buscar equipo de ventas del asesor
                    team = self.env['crm.team']._get_default_team_id(
                        user_id=partner.user_id.id
                    )
                    
                    # Crear la oportunidad automáticamente
                    lead_vals = {
                        'name': _("Oportunidad de %s") % partner.name,
                        'partner_id': partner.id,
                        'user_id': partner.user_id.id,
                        'team_id': team.id if team else False,
                        'type': 'opportunity',
                        'email_from': partner.email,
                        'phone': partner.phone or partner.mobile,
                        'contact_name': partner.name,
                        'description': _('Oportunidad creada automáticamente al registrar el contacto'),
                        'priority': '1',
                    }
                    
                    lead = self.env['crm.lead'].create(lead_vals)
                    _logger.info(f"Oportunidad creada: {lead.name} (ID: {lead.id}) - Asesor: {partner.user_id.name}")
        
        return partners
