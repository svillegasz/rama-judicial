import requests
from prefect import task
from typing import Dict, Any, List, Callable, Optional
import time
import random
from datetime import datetime
from http import HTTPStatus
from rama.utils.logging_utils import get_logger

logger = get_logger("tasks.api_client")

# -------------------------------------------------------------------------
# API Configuration
# -------------------------------------------------------------------------
API_BASE_URL = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2"
REQUEST_TIMEOUT = 30

# -------------------------------------------------------------------------
# Rate Limiting Configuration
# -------------------------------------------------------------------------
MIN_DELAY_SECONDS = 3.0
MAX_DELAY_SECONDS = 7.0
MAX_RETRIES = 3
RETRY_BACKOFF_FIRST = 30
RETRY_BACKOFF_SUBSEQUENT = 60
RATE_LIMIT_COOLDOWN = 60

# -------------------------------------------------------------------------
# User-Agent Rotation
# -------------------------------------------------------------------------
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

BASE_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Origin': 'https://consultaprocesos.ramajudicial.gov.co',
    'Connection': 'keep-alive',
    'Referer': 'https://consultaprocesos.ramajudicial.gov.co/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Priority': 'u=0'
}


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def get_random_headers() -> Dict[str, str]:
    """Generate headers with a random User-Agent for request rotation"""
    headers = BASE_HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers


def random_delay(min_seconds: float = MIN_DELAY_SECONDS, max_seconds: float = MAX_DELAY_SECONDS) -> None:
    """Add a randomized delay between requests to avoid rate limiting"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def make_api_request_with_retry(
    request_func: Callable[[], requests.Response],
    error_context: str,
    max_retries: int = MAX_RETRIES
) -> requests.Response:
    """
    Execute an API request with automatic retry logic for common errors.
    
    Args:
        request_func: Function that makes the actual HTTP request
        error_context: Context string for error messages (e.g., "proceso 123")
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response object if successful
        
    Raises:
        Exception: If all retry attempts fail or non-retryable error occurs
    """
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            # Add backoff delay on retries
            if retry_count > 0:
                backoff_time = RETRY_BACKOFF_SUBSEQUENT if retry_count > 1 else RETRY_BACKOFF_FIRST
                logger.info(f"Retry {retry_count}/{max_retries} for {error_context}, waiting {backoff_time}s...")
                time.sleep(backoff_time)
            
            response = request_func()
            
            # Handle specific HTTP status codes
            if response.status_code == HTTPStatus.FORBIDDEN:
                retry_count += 1
                logger.warning(f"Rate limit hit (403) for {error_context}. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    time.sleep(RATE_LIMIT_COOLDOWN)
                    continue
                raise Exception(f"Rate limit exceeded after {max_retries} retries")
            
            if response.status_code == HTTPStatus.NOT_FOUND:
                raise Exception(f"Resource not found (404): {error_context}")
            
            if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                retry_count += 1
                logger.warning(f"Server error {response.status_code} for {error_context}. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    time.sleep(RETRY_BACKOFF_FIRST)
                    continue
                raise Exception(f"Server error {response.status_code} after {max_retries} retries")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            last_exception = e
            logger.error(f"Request failed for {error_context}: {str(e)}")
            if retry_count < max_retries:
                time.sleep(RETRY_BACKOFF_FIRST)
                continue
            raise Exception(f"Request failed after {max_retries} retries: {str(e)}")
    
    # If we exhausted all retries
    raise Exception(f"Failed {error_context} after {max_retries} retries: {str(last_exception)}")


def select_most_recent_proceso(procesos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Select the most recent proceso from a list based on fechaUltimaActuacion.
    
    Args:
        procesos: List of proceso dictionaries
        
    Returns:
        The proceso with the most recent fechaUltimaActuacion, or first if none have that field
    """
    if len(procesos) == 1:
        return procesos[0]
    
    # Filter processes that have fechaUltimaActuacion
    procesos_with_fecha = [p for p in procesos if p.get('fechaUltimaActuacion')]
    
    if not procesos_with_fecha:
        logger.warning(f"No processes have fechaUltimaActuacion, returning first of {len(procesos)} processes")
        return procesos[0]
    
    # Return the process with the most recent date
    most_recent = max(
        procesos_with_fecha,
        key=lambda p: datetime.fromisoformat(p['fechaUltimaActuacion'].replace('Z', '+00:00').split('.')[0])
    )
    
    logger.info(f"Selected most recent of {len(procesos)} processes with fecha {most_recent.get('fechaUltimaActuacion')}")
    return most_recent


# -------------------------------------------------------------------------
# API Tasks
# -------------------------------------------------------------------------


@task
def get_proceso_by_radicacion(numero_radicacion: str) -> Dict[str, Any]:
    """
    Query proceso by radicacion number to get the idProceso.
    
    If multiple processes exist, returns the one with the most recent fechaUltimaActuacion.
    Includes automatic retry logic for rate limiting and server errors.
    
    Args:
        numero_radicacion: Process radicacion number (e.g., "05129310300120190018700")
        
    Returns:
        Dictionary with process basic information including idProceso
        
    Raises:
        Exception: If process not found or request fails after retries
    """
    logger.debug(f"Fetching proceso by radicacion: {numero_radicacion}")
    
    def make_request() -> requests.Response:
        url = f"{API_BASE_URL}/Procesos/Consulta/NumeroRadicacion"
        params = {
            'numero': numero_radicacion,
            'SoloActivos': 'false',
            'pagina': 1
        }
        return requests.get(url, headers=get_random_headers(), params=params, timeout=REQUEST_TIMEOUT)
    
    try:
        response = make_api_request_with_retry(
            make_request,
            error_context=f"proceso {numero_radicacion}"
        )
        
        data = response.json()
        
        # Validate response data
        if not data.get('procesos') or len(data['procesos']) == 0:
            raise Exception(f"No process found for radicacion: {numero_radicacion}")
        
        procesos = data['procesos']
        selected_proceso = select_most_recent_proceso(procesos)
        
        logger.debug(f"Successfully fetched proceso {selected_proceso.get('idProceso')} for radicacion {numero_radicacion}")
        return selected_proceso
        
    except Exception as e:
        logger.error(f"Failed to fetch proceso {numero_radicacion}: {str(e)}")
        raise Exception(f"Failed to fetch proceso by radicacion {numero_radicacion}: {str(e)}")


@task
def get_proceso_actuaciones(id_proceso: int, pagina: int = 1) -> List[Dict[str, Any]]:
    """
    Get actuaciones (actions/updates) for a specific proceso.
    
    Includes automatic retry logic for rate limiting and server errors.
    
    Args:
        id_proceso: Process ID obtained from get_proceso_by_radicacion
        pagina: Page number for pagination (default: 1)
        
    Returns:
        List of actuaciones with their details (sorted by most recent first)
        
    Raises:
        Exception: If actuaciones cannot be fetched after retries
    """
    logger.debug(f"Fetching actuaciones for proceso {id_proceso}, page {pagina}")
    
    def make_request() -> requests.Response:
        url = f"{API_BASE_URL}/Proceso/Actuaciones/{id_proceso}"
        params = {'pagina': pagina}
        return requests.get(url, headers=get_random_headers(), params=params, timeout=REQUEST_TIMEOUT)
    
    try:
        response = make_api_request_with_retry(
            make_request,
            error_context=f"actuaciones for proceso {id_proceso}"
        )
        
        data = response.json()
        actuaciones = data.get('actuaciones', [])
        
        logger.debug(f"Successfully fetched {len(actuaciones)} actuaciones for proceso {id_proceso}")
        return actuaciones
        
    except Exception as e:
        logger.error(f"Failed to fetch actuaciones for proceso {id_proceso}: {str(e)}")
        raise Exception(f"Failed to fetch actuaciones for proceso {id_proceso}: {str(e)}")


@task
def get_latest_actuacion(numero_radicacion: str) -> Dict[str, Any]:
    """
    Get the latest actuacion for a proceso by radicacion number.
    
    This is a convenience function that combines get_proceso_by_radicacion
    and get_proceso_actuaciones to fetch the most recent action.
    
    Args:
        numero_radicacion: Process radicacion number (e.g., "05129310300120190018700")
        
    Returns:
        Dictionary with the latest actuacion data containing:
        - fecha_actuacion: Date of the action
        - actuacion: Action description
        - anotacion: Additional notes
        - fecha_inicial: Start date (if applicable)
        - fecha_final: End date (if applicable)
        - fecha_registro: Registration date
        - id_proceso: Process ID
        - llave_proceso: Process key
        
    Raises:
        Exception: If proceso not found or has no actuaciones
    """
    logger.info(f"Fetching latest actuacion for {numero_radicacion}")
    
    try:
        # Get the proceso to obtain the idProceso
        proceso = get_proceso_by_radicacion(numero_radicacion)
        id_proceso = proceso['idProceso']
        
        # Add random delay between API calls to avoid rate limiting
        random_delay()
        
        # Get the actuaciones
        actuaciones = get_proceso_actuaciones(id_proceso)
        
        if not actuaciones:
            raise Exception(f"No actuaciones found for proceso: {numero_radicacion}")
        
        # The first actuacion is the most recent one
        latest = actuaciones[0]
        
        # Return normalized data structure
        result = {
            'fecha_actuacion': latest['fechaActuacion'],
            'actuacion': latest['actuacion'],
            'anotacion': latest.get('anotacion', ''),
            'fecha_inicial': latest.get('fechaInicial'),
            'fecha_final': latest.get('fechaFinal'),
            'fecha_registro': latest['fechaRegistro'],
            'id_proceso': id_proceso,
            'llave_proceso': latest['llaveProceso']
        }
        
        logger.info(f"Successfully fetched latest actuacion for {numero_radicacion}: {latest['actuacion']}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get latest actuacion for {numero_radicacion}: {str(e)}")
        raise Exception(f"Failed to get latest actuacion for {numero_radicacion}: {str(e)}")

