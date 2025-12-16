# Odoo Lion Seller - Configuración Personalizada

Este repositorio contiene las **personalizaciones y módulos custom** para Odoo 18.0 Community.

## Estructura del Proyecto

```
OdooLionSceller/
├── custom_addons/          # Módulos personalizados
│   └── theme_lionsceller/  # Tema personalizado
├── odoo/                   # Odoo core (no versionado, clonar aparte)
└── README.md
```

## Instalación en Otro Equipo

### 1. Clonar Odoo 18.0

```powershell
cd "C:\Users\TU_USUARIO\Documents"
git clone https://github.com/odoo/odoo.git --branch 18.0 --depth 1
cd odoo
```

### 2. Clonar este repositorio

```powershell
cd ..
git clone https://github.com/antonio406/odoo-lion.git OdooLionSceller
```

### 3. Mover los módulos personalizados

```powershell
Move-Item -Path "OdooLionSceller\custom_addons" -Destination "odoo\"
```

O configurar `addons_path` en `odoo.conf`:

```ini
addons_path = addons,../OdooLionSceller/custom_addons
```

### 4. Instalar dependencias de Python

```powershell
cd odoo
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install libsass
```

### 5. Configurar PostgreSQL

- Usuario: `odoo18`
- Password: `12345678`
- Puerto: `5432`

### 6. Ejecutar Odoo

```powershell
python odoo-bin -c odoo.conf
```

## Módulos Personalizados

- **theme_lionsceller**: Tema con menú estilo Enterprise

## Notas

- Este repo NO incluye el core de Odoo
- Clonar Odoo 18.0 separadamente desde el repositorio oficial
- Los módulos custom están en `custom_addons/`
