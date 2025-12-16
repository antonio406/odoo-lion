from odoo import models, api, _
from odoo.exceptions import UserError
import random


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to auto-assign salesperson if missing.
        """
        leads = super(CrmLead, self).create(vals_list)
        for lead in leads:
            if not lead.user_id:
                lead._auto_assign_salesperson()
        return leads
    
    def action_send_whatsapp(self):
        """Abre un wizard para enviar mensaje de WhatsApp"""
        self.ensure_one()
        
        # Verificar que el lead tenga teléfono
        phone = self.phone or self.mobile or (self.partner_id and (self.partner_id.phone or self.partner_id.mobile))
        
        if not phone:
            raise UserError(_('El lead no tiene un número de teléfono asociado.'))
        
        return {
            'name': _('Enviar WhatsApp'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead.send.whatsapp',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_phone': phone,
            }
        }
    
    def send_whatsapp_reminder(self, message=None):
        """
        Envía un recordatorio por WhatsApp
        Puede ser llamado desde acciones automatizadas
        """
        self.ensure_one()
        
        phone = self.phone or self.mobile or (self.partner_id and (self.partner_id.phone or self.partner_id.mobile))
        
        if not phone:
            return False
        
        if not message:
            message = _(
                "Hola %s,\n\n"
                "Te recordamos que tienes una oportunidad pendiente: %s\n\n"
                "¿En qué podemos ayudarte?\n\n"
                "Saludos,\n%s"
            ) % (
                self.partner_id.name or self.contact_name or 'Cliente',
                self.name,
                self.user_id.name if self.user_id else 'Equipo de Ventas'
            )
        
        whatsapp_helper = self.env['whatsapp.helper']
        result = whatsapp_helper.send_message(
            phone_number=phone,
            message=message,
            lead_id=self.id
        )
        
        return result.get('success', False)

    def _auto_assign_salesperson(self):
        """
        Assign a salesperson based on configured strategy.
        Strategies: round_robin, random, load_based
        """
        strategy = self.env['ir.config_parameter'].sudo().get_param(
            'lionsceller_crm.lead_assignment_strategy', 'round_robin'
        )
        
        if strategy == 'round_robin':
            user = self._get_next_salesperson_round_robin()
        elif strategy == 'random':
            user = self._get_random_salesperson()
        elif strategy == 'load_based':
            user = self._get_least_loaded_salesperson()
        else:
            user = self._get_next_salesperson_round_robin()  # Default fallback
        
        if user:
            self.user_id = user.id

    def _get_sales_team_users(self):
        """
        Get all active users in the sales team group.
        """
        sales_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
        if sales_group:
            # Filter only active users
            return sales_group.users.filtered(lambda u: u.active)
        return self.env['res.users']

    def _get_next_salesperson_round_robin(self):
        """
        Round Robin: Assign leads in rotation among all salespeople.
        Uses a counter stored in ir.config_parameter to track the last assigned user.
        """
        users = self._get_sales_team_users()
        if not users:
            return None
        
        # Get the last assigned user index
        last_index = int(self.env['ir.config_parameter'].sudo().get_param(
            'lionsceller_crm.last_assigned_index', '-1'
        ))
        
        # Calculate next index (circular)
        next_index = (last_index + 1) % len(users)
        
        # Update the counter
        self.env['ir.config_parameter'].sudo().set_param(
            'lionsceller_crm.last_assigned_index', str(next_index)
        )
        
        return users[next_index]

    def _get_random_salesperson(self):
        """
        Random: Assign a random salesperson from the sales team.
        """
        users = self._get_sales_team_users()
        if not users:
            return None
        
        return random.choice(users)

    def _get_least_loaded_salesperson(self):
        """
        Load-Based: Assign to the salesperson with the fewest active leads.
        Active leads are those not in 'Won' or 'Lost' stages.
        """
        users = self._get_sales_team_users()
        if not users:
            return None
        
        # Count active leads for each user
        user_loads = []
        for user in users:
            lead_count = self.env['crm.lead'].search_count([
                ('user_id', '=', user.id),
                ('active', '=', True),
                ('probability', '<', 100),  # Not won
                ('probability', '>', 0)      # Not lost
            ])
            user_loads.append((user, lead_count))
        
        # Sort by load (ascending) and return the user with minimum load
        user_loads.sort(key=lambda x: x[1])
        return user_loads[0][0] if user_loads else None

