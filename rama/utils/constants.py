from typing import Callable, NamedTuple, Final, Dict, Any
from datetime import datetime, timedelta

# -------------------------------------------------------------------------
# Data Types
# -------------------------------------------------------------------------
class Selector(NamedTuple):
    name: str
    css_selector: str
    result_type: str


# -------------------------------------------------------------------------
# URLs and Endpoints
# -------------------------------------------------------------------------
RAMA_URL: Final[str] = "https://procesos.ramajudicial.gov.co/procesoscs/ConsultaJusticias21.aspx"


# -------------------------------------------------------------------------
# HTML Selectors
# -------------------------------------------------------------------------
CIUDADES_SELECTOR: Final[str] = "select[id='ddlCiudad'] option"
ENTIDADES_SELECTOR: Final[str] = "select[id='ddlEntidadEspecialidad'] option"

PAYLOAD_SELECTORS: Final[list[Selector]] = [
    Selector("manager_script_hidden_field", "input[id='managerScript_HiddenField']", "value"),
    Selector("proceso_id", "input[id='txtNumeroProcesoID']", "value"),
    Selector(SESSION_ID_FIELD := "session_id", "input[id='nwoDediSpUsIdlroWehT_ID']", "value"),
]

DATA_SELECTORS: Final[list[Selector]] = [
    Selector(FECHA_ACTUACION_FIELD := "fecha_actuacion", "span[id='rptActuaciones_lblFechaActuacion_0']", "text"),
    Selector(ACTUACION_FIELD := "actuacion", "span[id='rptActuaciones_lblActuacion_0']", "text"),
    Selector(ANOTACION_FIELD := "anotacion", "span[id='rptActuaciones_lblAnotacion_0']", "text"),
    Selector(FECHA_INICIO_FIELD := "fecha_inicio", "span[id='rptActuaciones_lblFechaInicio_0']", "text"),
    Selector(FECHA_FIN_FIELD := "fecha_fin", "span[id='rptActuaciones_lblFechaFin_0']", "text"),
    Selector(FECHA_REGISTRO_FIELD := "fecha_registro", "span[id='rptActuaciones_lblFechaRegistro_0']", "text")
]


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
# Form Field Names
# -------------------------------------------------------------------------
CIUDAD_FIELD: Final[str] = "ciudad"
EVENT_TARGET_FIELD: Final[str] = "__EVENTTARGET"
MANAGER_SCRIPT_FIELD: Final[str] = "manager_script"
PROCESO_FIELD: Final[str] = "proceso"
ENTIDAD_FIELD: Final[str] = "entidad"


# -------------------------------------------------------------------------
# HTTP Request Constants
# -------------------------------------------------------------------------
ASP_NET_SESSION_ID: Final[str] = "ASP.NET_SessionId"

EMAIL_SUBJECT_TEMPLATE: Final[str] = "Notificación Rama Judicial"

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
    session_id_action = f"{payload[SESSION_ID_FIELD]}=Consultar" if payload[SESSION_ID_FIELD] else ""
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


def check_fecha(value):
    """Check if the date is recent (within the last 7 days)"""    
    if not value:
        return False
    
    try:
        # Parse the Spanish date format (e.g., "19 Oct 2022")
        months_es = {
            'Ene': 'Jan', 'Feb': 'Feb', 'Mar': 'Mar', 'Abr': 'Apr',
            'May': 'May', 'Jun': 'Jun', 'Jul': 'Jul', 'Ago': 'Aug',
            'Sep': 'Sep', 'Oct': 'Oct', 'Nov': 'Nov', 'Dic': 'Dec'
        }
        
        day, month_es, year = value.split()
        month_en = months_es.get(month_es, month_es)
        date_str = f"{day} {month_en} {year}"
        date = datetime.strptime(date_str, "%d %b %Y")
        
        # Check if the date is within the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        return date >= seven_days_ago
    except Exception:
        # If there's any error parsing the date, return False
        return False

# -------------------------------------------------------------------------
# Validation Rules
# -------------------------------------------------------------------------
VALIDATION_RULES: Final[dict[str, Callable]] = {
    FECHA_ACTUACION_FIELD: check_fecha,
}
