# Rama Judicial Automation

Sistema de automatización para la consulta y notificación de procesos judiciales.

## Características

- Consulta de procesos desde hojas de cálculo públicas de Google
- Extracción de datos de las páginas web de la Rama Judicial
- Sistema de validación configurable
- Notificaciones automáticas por correo electrónico
- Flujos de trabajo basados en Prefect para orquestación y monitoreo

## Requisitos

- Python 3.13+
- Las dependencias definidas en `pyproject.toml`
- Credenciales de Google para acceder a Google Sheets API

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/sebasvilz/rama-judicial.git
cd rama-judicial

# Instalar con Poetry
poetry install
```

### Configuración de Google Sheets API

1. Crea un proyecto en la [Google Cloud Console](https://console.cloud.google.com/)
2. Habilita la API de Google Sheets en tu proyecto
3. Crea credenciales de servicio desde la sección "Credenciales"
   - Selecciona "Cuenta de servicio" para crear una nueva cuenta de servicio
   - Descarga el archivo JSON de credenciales
4. Añade la ruta a tus credenciales en tu archivo `env`:
   ```
   GOOGLE_APPLICATION_CREDENTIALS="/ruta/completa/a/tu-archivo-credenciales.json"
   ```
5. Asegúrate de compartir tu hoja de cálculo con la dirección de correo de la cuenta de servicio

### Configuración del Entorno

Crea un archivo `env` en la raíz del proyecto con las siguientes variables:

```
SPREADSHEET_ID=tu-id-de-spreadsheet
GOOGLE_APPLICATION_CREDENTIALS=/ruta/completa/a/tu-archivo-credenciales.json
EMAIL_RECIPIENT=correo-para-notificaciones@ejemplo.com
SMTP_SERVER=tu-servidor-smtp.com
SMTP_USERNAME=tu-usuario-smtp
SMTP_PASSWORD=tu-contraseña-smtp
```

## Uso

### Ejecución de Flujos de Trabajo

El proyecto incluye dos flujos de trabajo principales:

#### 1. Revisar Procesos Judiciales

```bash
# Ejecutar el flujo de revisión de procesos
python revisar_procesos.py
```

También puedes usar el flujo programáticamente:

```python
from rama.workflows.procesos import revisar_procesos

# Ejecutar el flujo
result = revisar_procesos()
```

#### 2. Extraer Entidades Judiciales

```bash
# Sincronizar entidades desde la web de la Rama Judicial
python sync_entidades.py
```

También puedes usar el flujo programáticamente:

```python
from rama.workflows.entidades import extraer_entidades

# Ejecutar el flujo
result = extraer_entidades()
```

## Estructura

- `rama/tasks/`: Tareas atómicas para componer flujos de trabajo
- `rama/workflows/`: Flujos de trabajo que orquestan tareas
  - `procesos.py`: Flujo para revisar procesos judiciales
  - `entidades.py`: Flujo para extraer entidades judiciales
- `rama/utils/`: Utilidades y constantes
- `revisar_procesos.py`: Script para ejecutar el flujo de procesos
- `sync_entidades.py`: Script para ejecutar el flujo de entidades

## Licencia

MIT