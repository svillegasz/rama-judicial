import requests
from prefect import task
from typing import Dict, Any, List
import time
import random
from datetime import datetime

# API Base URL
API_BASE_URL = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2"

# List of User-Agent strings to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Base headers (User-Agent will be rotated)
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


def get_random_headers() -> Dict[str, str]:
    """Generate headers with a random User-Agent"""
    headers = BASE_HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers


def random_delay(min_seconds: float = 3.0, max_seconds: float = 7.0):
    """Add a randomized delay between requests"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


@task
def get_proceso_by_radicacion(numero_radicacion: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Query proceso by radicacion number to get the idProceso
    
    Args:
        numero_radicacion: Process radicacion number
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with process basic information including idProceso.
        If multiple processes exist, returns the one with the most recent fechaUltimaActuacion.
    """
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            # Add random delay before request (except first attempt)
            if retry_count > 0:
                backoff_time = 60 if retry_count > 1 else 30
                time.sleep(backoff_time)
            
            url = f"{API_BASE_URL}/Procesos/Consulta/NumeroRadicacion"
            params = {
                'numero': numero_radicacion,
                'SoloActivos': 'false',
                'pagina': 1
            }
            
            response = requests.get(url, headers=get_random_headers(), params=params, timeout=30)
            
            # Handle specific HTTP errors
            if response.status_code == 403:
                retry_count += 1
                last_exception = Exception(f"403 Forbidden - Rate limit likely hit. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    print(f"Rate limit hit, waiting 60 seconds before retry {retry_count}/{max_retries}...")
                    time.sleep(60)
                    continue
                else:
                    raise last_exception
            
            if response.status_code == 404:
                raise Exception(f"Process not found (404): {numero_radicacion}")
            
            if response.status_code >= 500:
                retry_count += 1
                last_exception = Exception(f"Server error {response.status_code}. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    time.sleep(30)
                    continue
                else:
                    raise last_exception
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check if we got results
            if not data.get('procesos') or len(data['procesos']) == 0:
                raise Exception(f"No process found for radicacion: {numero_radicacion}")
            
            procesos = data['procesos']
            
            # If only one process, return it
            if len(procesos) == 1:
                return procesos[0]
            
            # If multiple processes, find the one with fechaUltimaActuacion
            procesos_with_fecha = [p for p in procesos if p.get('fechaUltimaActuacion')]
            
            if not procesos_with_fecha:
                # If none have fechaUltimaActuacion, return the first one
                return procesos[0]
            
            # Return the process with the most recent fechaUltimaActuacion
            most_recent = max(procesos_with_fecha, 
                            key=lambda p: datetime.fromisoformat(p['fechaUltimaActuacion'].replace('Z', '+00:00').split('.')[0]))
            
            return most_recent
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            last_exception = e
            if retry_count < max_retries:
                time.sleep(30)
                continue
            else:
                raise Exception(f"Failed to fetch proceso by radicacion {numero_radicacion} after {max_retries} retries: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to fetch proceso by radicacion {numero_radicacion}: {str(e)}")
    
    # If we exhausted all retries
    if last_exception:
        raise Exception(f"Failed to fetch proceso by radicacion {numero_radicacion} after {max_retries} retries: {str(last_exception)}")


@task
def get_proceso_actuaciones(id_proceso: int, pagina: int = 1, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Get actuaciones for a specific proceso
    
    Args:
        id_proceso: Process ID obtained from get_proceso_by_radicacion
        pagina: Page number for pagination (default: 1)
        max_retries: Maximum number of retry attempts
        
    Returns:
        List of actuaciones with their details
    """
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            # Add random delay before request (except first attempt)
            if retry_count > 0:
                backoff_time = 60 if retry_count > 1 else 30
                time.sleep(backoff_time)
            
            url = f"{API_BASE_URL}/Proceso/Actuaciones/{id_proceso}"
            params = {'pagina': pagina}
            
            response = requests.get(url, headers=get_random_headers(), params=params, timeout=30)
            
            # Handle specific HTTP errors
            if response.status_code == 403:
                retry_count += 1
                last_exception = Exception(f"403 Forbidden - Rate limit likely hit. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    print(f"Rate limit hit, waiting 60 seconds before retry {retry_count}/{max_retries}...")
                    time.sleep(60)
                    continue
                else:
                    raise last_exception
            
            if response.status_code == 404:
                raise Exception(f"Actuaciones not found (404) for proceso: {id_proceso}")
            
            if response.status_code >= 500:
                retry_count += 1
                last_exception = Exception(f"Server error {response.status_code}. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    time.sleep(30)
                    continue
                else:
                    raise last_exception
            
            response.raise_for_status()
            
            data = response.json()
            
            # Return the actuaciones list
            return data.get('actuaciones', [])
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            last_exception = e
            if retry_count < max_retries:
                time.sleep(30)
                continue
            else:
                raise Exception(f"Failed to fetch actuaciones for proceso {id_proceso} after {max_retries} retries: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to fetch actuaciones for proceso {id_proceso}: {str(e)}")
    
    # If we exhausted all retries
    if last_exception:
        raise Exception(f"Failed to fetch actuaciones for proceso {id_proceso} after {max_retries} retries: {str(last_exception)}")


@task
def get_latest_actuacion(numero_radicacion: str) -> Dict[str, Any]:
    """
    Get the latest actuacion for a proceso by radicacion number
    
    Args:
        numero_radicacion: Process radicacion number
        
    Returns:
        Dictionary with the latest actuacion data
    """
    try:
        # First, get the proceso to obtain the idProceso
        proceso = get_proceso_by_radicacion(numero_radicacion)
        id_proceso = proceso['idProceso']
        
        # Add random delay between API calls
        random_delay()
        
        # Then, get the actuaciones
        actuaciones = get_proceso_actuaciones(id_proceso)
        
        if not actuaciones or len(actuaciones) == 0:
            raise Exception(f"No actuaciones found for proceso: {numero_radicacion}")
        
        # The first actuacion is the most recent one
        latest = actuaciones[0]
        
        # Return in a format similar to what the old web scraping returned
        return {
            'fecha_actuacion': latest['fechaActuacion'],
            'actuacion': latest['actuacion'],
            'anotacion': latest.get('anotacion', ''),
            'fecha_inicial': latest.get('fechaInicial'),
            'fecha_final': latest.get('fechaFinal'),
            'fecha_registro': latest['fechaRegistro'],
            'id_proceso': id_proceso,
            'llave_proceso': latest['llaveProceso']
        }
        
    except Exception as e:
        raise Exception(f"Failed to get latest actuacion for {numero_radicacion}: {str(e)}")

