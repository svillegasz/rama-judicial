from typing import Callable, Final, NamedTuple, Dict, Any
from datetime import datetime, timedelta

# -------------------------------------------------------------------------
# Data Types
# -------------------------------------------------------------------------
class Selector(NamedTuple):
    name: str
    css_selector: str
    result_type: str

# -------------------------------------------------------------------------
# Field Names (matching API response)
# -------------------------------------------------------------------------
FECHA_ACTUACION_FIELD: Final[str] = "fecha_actuacion"
ACTUACION_FIELD: Final[str] = "actuacion"
ANOTACION_FIELD: Final[str] = "anotacion"
FECHA_INICIO_FIELD: Final[str] = "fecha_inicial"
FECHA_FIN_FIELD: Final[str] = "fecha_final"
FECHA_REGISTRO_FIELD: Final[str] = "fecha_registro"


# -------------------------------------------------------------------------
# Excel Export Constants
# -------------------------------------------------------------------------
ENTIDADES_SHEET_NAME: Final[str] = "Entidades"
PROCESOS_SHEET_NAME: Final[str] = "Procesos"
SUMMARY_SHEET_NAME: Final[str] = "Reporte"

ENTIDAD_COLUMN: Final[str] = "entidad"
VALOR_COLUMN: Final[str] = "valor"
RADICADO_COLUMN: Final[str] = "radicado"

ENTIDADES_COLUMNS: Final[list[str]] = [ENTIDAD_COLUMN, VALOR_COLUMN]


# -------------------------------------------------------------------------
# Legacy Web Scraping Constants (still used by entidades workflow)
# -------------------------------------------------------------------------
RAMA_URL: Final[str] = "https://procesos.ramajudicial.gov.co/procesoscs/ConsultaJusticias21.aspx"
CIUDADES_SELECTOR: Final[str] = "select[id='ddlCiudad'] option"
ENTIDADES_SELECTOR: Final[str] = "select[id='ddlEntidadEspecialidad'] option"
ASP_NET_SESSION_ID: Final[str] = "ASP.NET_SessionId"

SESSION_ID_FIELD: Final[str] = "session_id"
CIUDAD_FIELD: Final[str] = "ciudad"
EVENT_TARGET_FIELD: Final[str] = "__EVENTTARGET"
MANAGER_SCRIPT_FIELD: Final[str] = "manager_script"

PAYLOAD_SELECTORS: Final[list[Selector]] = [
    Selector("manager_script_hidden_field", "input[id='managerScript_HiddenField']", "value"),
    Selector("proceso_id", "input[id='txtNumeroProcesoID']", "value"),
    Selector(SESSION_ID_FIELD, "input[id='nwoDediSpUsIdlroWehT_ID']", "value"),
]

PAYLOAD_TEMPLATE: Final[str] = "managerScript={manager_script}&managerScript_HiddenField={manager_script_hidden_field}&ddlCiudad={ciudad}&ddlEntidadEspecialidad={entidad}&rblConsulta=1&{proceso_id}={proceso}&SliderNumeroProceso=1&ddlTipoSujeto=0&ddlTipoPersona=0&SliderConsultaNom=0&ddlYear=...&tbxNumeroConstruido=050013103&SliderConstruirNumero=0&ddlTipoSujeto2=0&ddlTipoPersona2=0&SliderActFecha=0&SliderMagistrado=0&ddlTipoPersonaCN=1&SliderConsultaIdSujeto=0&HumanVerification=SLIDER&txtNumeroProcesoID={proceso_id}&nwoDediSpUsIdlroWehT_ID={session_id}&ddlJuzgados=0&hdControl=&BotDetector=BotValue&__EVENTTARGET=&__EVENTARGUMENT=&__LASTFOCUS=&__VIEWSTATE=&__ASYNCPOST=true&{session_id_action}"

RAMA_HEADERS: Final[dict[str, str]] = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'X-Requested-With': 'XMLHttpRequest',
    'X-MicrosoftAjax': 'Delta=true',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
    'Origin': 'https://procesos.ramajudicial.gov.co',
    'Connection': 'keep-alive',
    'Referer': 'https://procesos.ramajudicial.gov.co/procesoscs/ConsultaJusticias21.aspx',
    'Cookie': 'ASP.NET_SessionId=oyauyt5wodatpi4yv3cqkr34',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Priority': 'u=0'
}


# -------------------------------------------------------------------------
# Email Configuration
# -------------------------------------------------------------------------
EMAIL_SUBJECT_TEMPLATE: Final[str] = "Notificación Rama Judicial"


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def format_payload_template(payload: Dict[str, Any]) -> str:
    """
    Format the payload template with the given payload dictionary.
    Missing variables will be replaced with empty strings instead of raising an error.
    
    Args:
        payload: Dictionary with payload parameters
        
    Returns:
        Formatted payload string
    """
    session_id_action = f"{payload[SESSION_ID_FIELD]}=Consultar" if payload.get(SESSION_ID_FIELD) else ""
    payload["session_id_action"] = session_id_action
    
    class DefaultDict(dict):
        def __missing__(self, key):
            return ""
    
    # Create a new dictionary with default values for missing keys
    safe_payload = DefaultDict(payload)
    
    # Format the payload template with the safe dictionary
    return PAYLOAD_TEMPLATE.format_map(safe_payload)


def extract_session_cookie(response) -> str:
    """
    Extract the ASP.NET_SessionId cookie from a response
    
    Args:
        response: Requests response object
        
    Returns:
        Session ID string or empty string if not found
    """
    if ASP_NET_SESSION_ID in response.cookies:
        return response.cookies[ASP_NET_SESSION_ID]
    return ""


def check_fecha(value, days_range: int = 7):
    """Check if the date is recent (within the last n days)
    
    Always uses ISO format parsing (2025-02-12T00:00:00)
    """    
    if not value:
        return False
    
    try:
        # Parse ISO format from API: "2025-02-12T00:00:00"
        date = datetime.fromisoformat(value.replace('Z', '+00:00').split('.')[0])
        
        # Check if the date is within the last n days
        days_ago = datetime.now() - timedelta(days=days_range)
        return date >= days_ago
    except Exception:
        raise Exception(f"Error parsing date: {value}")


def check_fecha_older_than_months(value, months: int = 6):
    """Check if the date is older than n months
    
    Always uses ISO format parsing (2025-02-12T00:00:00)
    """    
    if not value:
        return False
    
    try:
        # Parse ISO format from API: "2025-02-12T00:00:00"
        date = datetime.fromisoformat(value.replace('Z', '+00:00').split('.')[0])
        
        # Check if the date is older than n months
        months_ago = datetime.now() - timedelta(days=months * 30)  # Approximate months as 30 days
        return date < months_ago
    except Exception:
        raise Exception(f"Error parsing date: {value}")


def format_date_for_display(value):
    """Format ISO date to Spanish format: day-month-year (e.g., "10-Oct-2025")
    
    Args:
        value: ISO date string like "2025-02-12T00:00:00"
        
    Returns:
        Formatted date like "12-Feb-2025"
    """
    if not value:
        return ""
    
    try:
        # Parse ISO format from API: "2025-02-12T00:00:00"
        date = datetime.fromisoformat(value.replace('Z', '+00:00').split('.')[0])
        
        # Convert to Spanish month abbreviations
        months_en_to_es = {
            'Jan': 'Ene', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Abr',
            'May': 'May', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
            'Sep': 'Sep', 'Oct': 'Oct', 'Nov': 'Nov', 'Dec': 'Dic'
        }
        month_abbr = date.strftime("%b")
        month_es = months_en_to_es.get(month_abbr, month_abbr)
        
        # Format as day-month-year
        return f"{date.day:02d}-{month_es}-{date.year}"
    except Exception:
        return value

