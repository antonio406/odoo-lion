# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLeadSendWhatsApp(models.TransientModel):
    _name = 'crm.lead.send.whatsapp'
    _description = 'Enviar WhatsApp desde Lead/Oportunidad'

    lead_id = fields.Many2one('crm.lead', string='Lead/Oportunidad', required=True)
    phone = fields.Char(string='Número de WhatsApp', required=True)
    message = fields.Text(string='Mensaje', required=True, default=lambda self: self._default_message())
    
    @api.model
    def _default_message(self):
        """Mensaje predeterminado"""
        lead_id = self.env.context.get('default_lead_id')
        if lead_id:
            lead = self.env['crm.lead'].browse(lead_id)
            user_name = lead.user_id.name if lead.user_id else 'Equipo de Ventas'
            partner_name = lead.partner_id.name or lead.contact_name or 'Cliente'
            
            return _(
                "Hola %s,\n\n"
                "Te contacto de %s respecto a: %s\n\n"
                "¿En qué momento te vendría bien conversar?\n\n"
                "Saludos,\n%s"
            ) % (
                partner_name,
                self.env.company.name,
                lead.name,
                user_name
            )
        return ''
    
    def action_send(self):
        """Envía el mensaje de WhatsApp"""
        self.ensure_one()
        
        whatsapp_helper = self.env['whatsapp.helper']
        
        result = whatsapp_helper.send_message(
            phone_number=self.phone,
            message=self.message,
            lead_id=self.lead_id.id
        )
        
        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('¡WhatsApp Enviado!'),
                    'message': _('El mensaje fue enviado exitosamente a %s') % self.phone,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_(
                'Error al enviar WhatsApp:\n%s'
            ) % result.get('message', 'Error desconocido'))
