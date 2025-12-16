# -*- coding: utf-8 -*-
import logging
import requests
import json
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppHelper(models.AbstractModel):
    """Helper model para enviar mensajes de WhatsApp vía Meta Cloud API"""
    _name = 'whatsapp.helper'
    _description = 'WhatsApp Helper'

    def send_message(self, phone_number, message, partner_id=None, lead_id=None):
        """
        Envía un mensaje de WhatsApp usando Meta Cloud API
        
        :param phone_number: Número de teléfono (con código de país, ej: +521234567890)
        :param message: Texto del mensaje a enviar
        :param partner_id: ID del partner (opcional, para logging)
        :param lead_id: ID del lead (opcional, para logging)
        :return: dict con resultado del envío
        """
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Obtener configuración
        access_token = ICP.get_param('lionsceller_crm.whatsapp_access_token')
        phone_number_id = ICP.get_param('lionsceller_crm.whatsapp_phone_number_id')
        test_mode = ICP.get_param('lionsceller_crm.whatsapp_test_mode', 'False') == 'True'
        
        # MODO DE PRUEBA: Simular envío sin configuración
        if test_mode or not access_token or not phone_number_id:
            _logger.warning("⚠️ MODO DE PRUEBA - WhatsApp no se enviará realmente")
            
            if lead_id:
                lead = self.env['crm.lead'].browse(lead_id)
                lead.message_post(
                    body=_("📱 [MODO PRUEBA] Mensaje de WhatsApp simulado a %s:<br/><i>%s</i>") % (phone_number, message),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
            
            return {
                'success': True,
                'message': 'Mensaje simulado (modo prueba)',
                'test_mode': True
            }
        
        # Limpiar número de teléfono (quitar espacios, guiones, etc)
        phone_clean = ''.join(filter(str.isdigit, phone_number))
        
        # Si no tiene código de país, agregar el de México por defecto
        if not phone_clean.startswith('52') and len(phone_clean) == 10:
            phone_clean = '52' + phone_clean
        
        # Preparar el payload para Meta Cloud API
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_clean,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        _logger.info(f"Enviando WhatsApp a {phone_clean}: {message[:50]}...")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response_data = response.json()
            
            if response.status_code == 200:
                _logger.info(f"✅ WhatsApp enviado exitosamente: {response_data}")
                
                # Registrar en el chatter si es un lead
                if lead_id:
                    lead = self.env['crm.lead'].browse(lead_id)
                    lead.message_post(
                        body=_("📱 Mensaje de WhatsApp enviado:<br/><i>%s</i>") % message,
                        message_type='comment',
                        subtype_xmlid='mail.mt_note'
                    )
                
                return {
                    'success': True,
                    'message': 'Mensaje enviado exitosamente',
                    'response': response_data
                }
            else:
                error_msg = response_data.get('error', {}).get('message', 'Error desconocido')
                _logger.error(f"❌ Error enviando WhatsApp: {response_data}")
                
                return {
                    'success': False,
                    'message': error_msg,
                    'response': response_data
                }
                
        except requests.exceptions.RequestException as e:
            _logger.error(f"❌ Error de conexión al enviar WhatsApp: {str(e)}")
            raise UserError(_(
                'Error al conectar con WhatsApp API:\n%s'
            ) % str(e))
        except Exception as e:
            _logger.error(f"❌ Error inesperado enviando WhatsApp: {str(e)}")
            raise UserError(_(
                'Error al enviar WhatsApp:\n%s'
            ) % str(e))
