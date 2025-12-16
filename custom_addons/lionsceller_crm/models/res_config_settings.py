from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lead_assignment_strategy = fields.Selection([
        ('round_robin', 'Round Robin (Rotación)'),
        ('random', 'Random (Aleatorio)'),
        ('load_based', 'Load-Based (Por Carga de Trabajo)')
    ], string='Estrategia de Asignación de Leads',
       default='round_robin',
       config_parameter='lionsceller_crm.lead_assignment_strategy',
       help='Selecciona cómo se asignarán automáticamente los asesores a los nuevos leads.')
    
    # WhatsApp Cloud API Configuration
    whatsapp_test_mode = fields.Boolean(
        string='Modo de Prueba',
        config_parameter='lionsceller_crm.whatsapp_test_mode',
        default=True,
        help='Si está activo, simula el envío de WhatsApp sin enviar mensajes reales (útil para pruebas)'
    )
    
    whatsapp_access_token = fields.Char(
        string='WhatsApp Access Token',
        config_parameter='lionsceller_crm.whatsapp_access_token',
        help='Token de acceso de Meta Cloud API para WhatsApp'
    )
    
    whatsapp_phone_number_id = fields.Char(
        string='WhatsApp Phone Number ID',
        config_parameter='lionsceller_crm.whatsapp_phone_number_id',
        help='ID del número de teléfono de WhatsApp Business'
    )
    
    whatsapp_verify_token = fields.Char(
        string='Webhook Verify Token',
        config_parameter='lionsceller_crm.whatsapp_verify_token',
        default='LIONSCELLER_SECRET_TOKEN',
        help='Token de verificación del webhook (debe coincidir con el configurado en Meta)'
    )
