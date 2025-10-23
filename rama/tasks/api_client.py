import requests
from prefect import task
from typing import Dict, Any, List

# API Base URL
API_BASE_URL = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2"

# API Headers based on the curl example
API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
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


@task
def get_proceso_by_radicacion(numero_radicacion: str) -> Dict[str, Any]:
    """
    Query proceso by radicacion number to get the idProceso
    
    Args:
        numero_radicacion: Process radicacion number
        
    Returns:
        Dictionary with process basic information including idProceso
    """
    try:
        url = f"{API_BASE_URL}/Procesos/Consulta/NumeroRadicacion"
        params = {
            'numero': numero_radicacion,
            'SoloActivos': 'false',
            'pagina': 1
        }
        
        response = requests.get(url, headers=API_HEADERS, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we got results
        if not data.get('procesos') or len(data['procesos']) == 0:
            raise Exception(f"No process found for radicacion: {numero_radicacion}")
        
        # Return the first process (should only be one)
        return data['procesos'][0]
        
    except Exception as e:
        raise Exception(f"Failed to fetch proceso by radicacion {numero_radicacion}: {str(e)}")


@task
def get_proceso_actuaciones(id_proceso: int, pagina: int = 1) -> List[Dict[str, Any]]:
    """
    Get actuaciones for a specific proceso
    
    Args:
        id_proceso: Process ID obtained from get_proceso_by_radicacion
        pagina: Page number for pagination (default: 1)
        
    Returns:
        List of actuaciones with their details
    """
    try:
        url = f"{API_BASE_URL}/Proceso/Actuaciones/{id_proceso}"
        params = {'pagina': pagina}
        
        response = requests.get(url, headers=API_HEADERS, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Return the actuaciones list
        return data.get('actuaciones', [])
        
    except Exception as e:
        raise Exception(f"Failed to fetch actuaciones for proceso {id_proceso}: {str(e)}")


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

