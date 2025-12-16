# Creación Automática de Leads y Envío de WhatsApp

## Funcionalidades

Este módulo extiende la funcionalidad del módulo CRM de Odoo para:

1. **Crear automáticamente oportunidades** cuando se registra un nuevo cliente/contacto
2. **Asignar automáticamente asesores** si no se especifica uno
3. **Enviar mensajes de WhatsApp** directamente desde las oportunidades

## 1. Creación Automática de Oportunidades

### Cómo funciona

1. **Al crear un contacto**: Cuando creas un nuevo contacto en Odoo (módulo Contactos)
2. **Asignación automática**: 
   - Si asignas un asesor → Se usa ese asesor
   - Si NO asignas asesor → El sistema asigna el primer vendedor disponible
3. **Oportunidad automática**: El sistema crea automáticamente una oportunidad con:
   - Nombre: "Oportunidad de [Nombre del Cliente]"
   - Cliente vinculado al contacto creado
   - Asesor asignado (manual o automático)
   - Equipo de ventas del asesor
   - Tipo: Oportunidad (aparece directamente en Pipeline)
   - Email y teléfono del contacto

### Uso

1. Ve a **Contactos** > **Crear**
2. Completa los datos del cliente (nombre, email, teléfono)
3. **Opcional**: En la pestaña **Ventas y Compras**, asigna un **Asesor de Ventas**
4. **Guarda** el contacto
5. Automáticamente aparecerá la oportunidad en **CRM** > **Pipeline**

## 2. Envío de Mensajes de WhatsApp

### Configuración Inicial (REQUERIDO)

Para enviar mensajes de WhatsApp necesitas configurar la **WhatsApp Cloud API de Meta**:

#### Paso 1: Obtener credenciales de Meta

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Crea una App de WhatsApp Business
3. Obtén:
   - **Access Token** (Token de acceso permanente)
   - **Phone Number ID** (ID del número de teléfono)

#### Paso 2: Configurar en Odoo

1. Ve a **Configuración** > **CRM**
2. Busca la sección **"WhatsApp Cloud API"**
3. Completa:
   - **WhatsApp Access Token**: Tu token de Meta
   - **Phone Number ID**: ID del número de WhatsApp Business
   - **Webhook Verify Token**: Deja el predeterminado o cambia (debe coincidir con Meta)
4. **Guarda**

#### Paso 3: Configurar Webhook en Meta

1. En tu App de Meta, ve a **WhatsApp** > **Configuration**
2. En **Webhook**, configura:
   - **Callback URL**: `https://tu-dominio.com/whatsapp/webhook`
   - **Verify Token**: El mismo que configuraste en Odoo
3. Suscríbete a los eventos: `messages`

### Enviar WhatsApp desde una Oportunidad

Una vez configurado:

1. Abre cualquier **Oportunidad** en CRM
2. Haz clic en el botón **📱 WhatsApp** (arriba en el header)
3. Se abre un formulario con:
   - Número de teléfono (pre-llenado del contacto)
   - Mensaje (con plantilla predeterminada editable)
4. **Envía** el mensaje
5. El mensaje queda registrado en el chatter de la oportunidad

### Enviar Recordatorios Automáticos

También puedes enviar recordatorios desde:

- **Acción masiva**: Selecciona varias oportunidades > Acción > "Enviar Recordatorio WhatsApp"
- **Código Python**: Llama a `lead.send_whatsapp_reminder()` desde una acción automatizada

## Notas

- Solo se crea la oportunidad si el contacto NO es un contacto hijo de una empresa
- El lead aparece directamente como **Oportunidad** en el Pipeline (no como Lead)
- Para WhatsApp, el número debe estar registrado en WhatsApp Business
- Los mensajes de WhatsApp requieren que el cliente haya iniciado conversación o tengas una plantilla aprobada

## Archivos del Módulo

- `models/res_partner.py`: Creación automática de oportunidades al crear contactos
- `models/crm_lead.py`: Métodos para enviar WhatsApp desde oportunidades
- `models/whatsapp_helper.py`: Helper para enviar mensajes vía Meta Cloud API
- `models/res_config_settings.py`: Configuración de WhatsApp
- `wizard/crm_lead_send_whatsapp.py`: Wizard para enviar WhatsApp
- `views/res_partner_views.xml`: Vista personalizada de contactos
- `views/crm_lead_views.xml`: Botón de WhatsApp en oportunidades
- `views/res_config_settings_views.xml`: Configuración en Settings
- `controllers/whatsapp_webhook.py`: Webhook para recibir mensajes de WhatsApp

## Soporte

Para más información sobre WhatsApp Cloud API:
- [Documentación oficial de Meta](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Guía de inicio rápido](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)

