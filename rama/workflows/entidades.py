from prefect import flow
from rama.tasks.web_scraping import fetch_html_content, extract_data_from_page, submit_payload
from rama.tasks.google_drive import update_spreadsheet_data
from rama.utils.constants import (
    PAYLOAD_SELECTORS, RAMA_URL, CIUDADES_SELECTOR, ENTIDADES_SELECTOR, 
    ENTIDADES_SHEET_NAME, CIUDAD_FIELD, MANAGER_SCRIPT_FIELD,
    EVENT_TARGET_FIELD, ENTIDADES_COLUMNS
)
import pandas as pd

@flow(name="Extraer Entidades")
def extraer_entidades():
    """
    Extracts entidades from the RAMA website and updates the Google Sheet.
    """
    soup = fetch_html_content(RAMA_URL)
    ciudades = soup.select(CIUDADES_SELECTOR)
    ciudades = [(ciudad.get_text(strip=True), ciudad.get("value")) for ciudad in ciudades]
    payload = extract_data_from_page(soup, PAYLOAD_SELECTORS)
    payload[EVENT_TARGET_FIELD] = "ddlCiudad"
    payload[MANAGER_SCRIPT_FIELD] = 'upPanelCiudad|ddlCiudad'

    all_entidades_list = []
        
    for ciudad, value in ciudades:
        if value == "0" or value == "":
            continue
        payload[CIUDAD_FIELD] = value
        soup = submit_payload(RAMA_URL, payload)
        entidades = soup.select(ENTIDADES_SELECTOR)
        entidades_list = [(entidad.get_text(strip=True), entidad.get("value")) for entidad in entidades 
                          if entidad.get("value") != "0" and entidad.get("value") != ""]
        all_entidades_list.extend(entidades_list)
    
    entidades = pd.DataFrame(all_entidades_list, columns=ENTIDADES_COLUMNS)
    update_spreadsheet_data(entidades, sheet_name=ENTIDADES_SHEET_NAME)