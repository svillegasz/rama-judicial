from prefect import flow
from rama.tasks.web_scraping import fetch_html_content, extract_data_from_page, submit_payload
from rama.tasks.google_drive import update_spreadsheet_data
from rama.utils.constants import (
    PAYLOAD_SELECTORS, RAMA_URL, CIUDADES_SELECTOR, ENTIDADES_SELECTOR, 
    ENTIDADES_SHEET_NAME, CIUDAD_FIELD, MANAGER_SCRIPT_FIELD,
    EVENT_TARGET_FIELD, ENTIDADES_COLUMNS
)
from rama.utils.logging_utils import get_logger
import pandas as pd

# Configure logging
logger = get_logger("workflows.entidades")

@flow(name="Extraer Entidades")
def extraer_entidades():
    """
    Extracts entidades from the RAMA website and updates the Google Sheet.
    """
    logger.info("Starting entidades extraction workflow")
    
    logger.info("Fetching initial HTML content from the RAMA website")
    soup = fetch_html_content(RAMA_URL)
    
    logger.info("Extracting available cities")
    ciudades = soup.select(CIUDADES_SELECTOR)
    ciudades = [(ciudad.get_text(strip=True), ciudad.get("value")) for ciudad in ciudades]
    logger.info(f"Found {len(ciudades)} cities")
    
    logger.info("Extracting form payload data")
    payload = extract_data_from_page(soup, PAYLOAD_SELECTORS)
    payload[EVENT_TARGET_FIELD] = "ddlCiudad"
    payload[MANAGER_SCRIPT_FIELD] = 'upPanelCiudad|ddlCiudad'

    all_entidades_list = []
        
    for ciudad, value in ciudades:
        if value == "0" or value == "":
            logger.debug(f"Skipping city with invalid value: {ciudad}")
            continue
            
        logger.info(f"Processing city: {ciudad} (value: {value})")
        payload[CIUDAD_FIELD] = value
        
        try:
            soup = submit_payload(RAMA_URL, payload)
            entidades = soup.select(ENTIDADES_SELECTOR)
            
            entidades_list = [(entidad.get_text(strip=True), entidad.get("value")) for entidad in entidades 
                            if entidad.get("value") != "0" and entidad.get("value") != ""]
                            
            logger.info(f"Found {len(entidades_list)} entities for {ciudad}")
            all_entidades_list.extend(entidades_list)
        except Exception as e:
            logger.error(f"Error processing city {ciudad}: {str(e)}")
            raise e
    
    logger.info(f"Total entities found: {len(all_entidades_list)}")
    entidades = pd.DataFrame(all_entidades_list, columns=ENTIDADES_COLUMNS)
    
    logger.info(f"Updating Google Spreadsheet with {len(entidades)} entities")
    update_spreadsheet_data(entidades, sheet_name=ENTIDADES_SHEET_NAME)
    
    logger.info("Entidades extraction workflow completed successfully")
    return entidades