import logging
import json
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class WhatsAppWebhook(http.Controller):
    
    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_webhook(self, **kwargs):
        """
        Verification step for Meta Webhook.
        Meta sends: hub.mode, hub.verify_token, hub.challenge
        """
        verify_token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')
        mode = kwargs.get('hub.mode')
        
        # TODO: Move this token to a system parameter or configuration setting
        MY_VERIFY_TOKEN = 'LIONSCELLER_SECRET_TOKEN'
        
        if mode and verify_token:
            if mode == 'subscribe' and verify_token == MY_VERIFY_TOKEN:
                _logger.info('WEBHOOK_VERIFIED')
                return Response(challenge, status=200)
            else:
                return Response('Forbidden', status=403)
        return Response('Bad Request', status=400)

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_message(self, **kwargs):
        """Receive and process incoming WhatsApp messages."""
        _logger.info("--------------- WHATSAPP WEBHOOK RECEIVED ---------------")
        _logger.info(f"Headers: {dict(request.httprequest.headers)}")
        _logger.info(f"Raw data: {request.httprequest.data}")
        _logger.info(f"Content-Type: {request.httprequest.content_type}")
        
        try:
            data = json.loads(request.httprequest.data)
        except Exception as e:
            _logger.error(f"FAILED TO PARSE JSON: {e}")
            _logger.error(f"Raw data was: {request.httprequest.data}")
            return Response("Bad Request", status=400)
            
        _logger.info(f"PAYLOAD: {data}")

        try:
            if 'entry' in data:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        # Log what kind of event this is
                        if 'messages' in value:
                            _logger.info("EVENT TYPE: MESSAGE RECEIVED")
                            for message in value['messages']:
                                self._process_incoming_message(message)
                        elif 'statuses' in value:
                            _logger.info("EVENT TYPE: STATUS UPDATE (Read/Delivered) - Ignoring")
                        else:
                            _logger.info(f"EVENT TYPE: OTHER ({list(value.keys())})")
            
            return Response('EVENT_RECEIVED', status=200)
        except Exception as e:
            _logger.error(f"ERROR PROCESSING WEBHOOK: {str(e)}")
            return Response('Error', status=500)

    def _process_incoming_message(self, message):
        """Process a single message and create/update Odoo records."""
        phone = message.get('from')
        body = message.get('text', {}).get('body', '')
        
        if not body and message.get('type') == 'button':
             body = message.get('button', {}).get('text', '')

        _logger.info(f"EXTRACTED DATA - Phone: {phone}, Body: {body}")

        if not phone:
            _logger.warning("No phone number found in message")
            return

        Partner = request.env['res.partner'].sudo()
        Lead = request.env['crm.lead'].sudo()

        # 1. Find or Create Partner
        partner = Partner.search([('phone', 'ilike', phone)], limit=1)
        if not partner:
            partner = Partner.search([('mobile', 'ilike', phone)], limit=1)
        
        if not partner:
            _logger.info(f"Creating new partner for {phone}")
            partner = Partner.create({
                'name': f'WhatsApp User {phone}',
                'phone': phone,
                'mobile': phone,
            })
        else:
            _logger.info(f"Found existing partner: {partner.name}")

        # 2. Create Lead/Opportunity
        source = request.env.ref('crm.source_newsletter', raise_if_not_found=False)
        
        lead_vals = {
            'name': f'WhatsApp: {body[:30]}...' if body else 'New WhatsApp Message',
            'partner_id': partner.id,
            'description': f"Message received: {body}\nPhone: {phone}",
            'type': 'opportunity',
            'source_id': source.id if source else False,
        }
        
        new_lead = Lead.create(lead_vals)
        _logger.info(f"LEAD CREATED: ID {new_lead.id} - {new_lead.name}")
