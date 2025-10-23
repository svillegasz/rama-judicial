import os
import pandas as pd
from prefect import flow
import logging

from rama.tasks.google_drive import get_spreadsheet_data, update_spreadsheet_data 
from rama.tasks.web_scraping import (
    fetch_html_content, 
    submit_payload,
    extract_data_from_page, 
    validate_data
)
from rama.tasks.notifications import generate_summary_report, send_email_notification, format_notification_message
from rama.utils.constants import (
    PAYLOAD_SELECTORS, 
    DATA_SELECTORS, 
    RAMA_URL, 
    PROCESOS_SHEET_NAME,
    ENTIDADES_SHEET_NAME,
    CIUDAD_FIELD,
    PROCESO_FIELD,
    ENTIDAD_FIELD,
    MANAGER_SCRIPT_FIELD,
    SESSION_ID_FIELD,
    RADICADO_COLUMN,
    ENTIDAD_COLUMN,
    SUMMARY_SHEET_NAME,
    VALIDATION_RULES,
    VALOR_COLUMN,
    EMAIL_SUBJECT_TEMPLATE,
    check_fecha_older_than_months,
    FECHA_ACTUACION_FIELD
)
from rama.utils.logging_utils import get_logger

# Configure logging
logger = get_logger("workflows.procesos")

@flow(name="Revisar Procesos Judiciales")
def revisar_procesos():
    """
    Flow to review judicial processes from a spreadsheet list,
    extract information from each process page, and send notifications
    when certain conditions are met.
    """  
    procesos_df = get_spreadsheet_data(sheet_name=PROCESOS_SHEET_NAME)
    entidades_df = get_spreadsheet_data(sheet_name=ENTIDADES_SHEET_NAME)
    procesos_to_notify = []
    procesos_to_impulsar = []
    procesos_to_review = []
    
    # Log the start of the process
    logger.info("Starting process review workflow")
    logger.info(f"Found {len(procesos_df)} processes to check")
        
    for index, proceso in procesos_df.iterrows():
        try:        
            logger.info(f"Processing process {proceso[RADICADO_COLUMN]}")
            soup = fetch_html_content(RAMA_URL)
            payload = extract_data_from_page(soup, PAYLOAD_SELECTORS)
            payload[CIUDAD_FIELD] = proceso[RADICADO_COLUMN][:5]
            payload[PROCESO_FIELD] = proceso[RADICADO_COLUMN]
            payload[MANAGER_SCRIPT_FIELD] = f'managerScript|{payload[SESSION_ID_FIELD]}'
            
            entidad_row = entidades_df[entidades_df[ENTIDAD_COLUMN] == proceso[ENTIDAD_COLUMN]]
            payload[ENTIDAD_FIELD] = entidad_row[VALOR_COLUMN].iloc[0]
            
            # Intermediate step to get the form state
            submit_payload(RAMA_URL, payload)

            # Submit form with the payload
            soup = submit_payload(RAMA_URL, payload)
            
            data = extract_data_from_page(soup, DATA_SELECTORS)
            
            is_valid, messages = validate_data(data, VALIDATION_RULES)
            
            # Check if the process is older than 6 months and needs to be impulsado
            if FECHA_ACTUACION_FIELD in data and check_fecha_older_than_months(data[FECHA_ACTUACION_FIELD], 6):
                logger.info(f"Process {proceso[RADICADO_COLUMN]} is older than 6 months, adding to impulsar list")
                procesos_to_impulsar.append({proceso[RADICADO_COLUMN]: data})
            elif is_valid:
                logger.info(f"Validation passed for process {proceso[RADICADO_COLUMN]}, adding to notification list")
                procesos_to_notify.append({proceso[RADICADO_COLUMN]: data})            
            else:
                logger.info(f"Process {proceso[RADICADO_COLUMN]} did not meet notification criteria: {messages}")
        except Exception as e:
            procesos_to_review.append({proceso[RADICADO_COLUMN]: str(e)})
            logger.error(f"Error processing process {proceso[RADICADO_COLUMN]}: {e}")

    if not procesos_to_notify and not procesos_to_impulsar and not procesos_to_review:
        logger.info("No processes to notify or review")
    else:
        logger.info("Generating summary report")
        summary_df = generate_summary_report(procesos_to_notify, procesos_to_impulsar, procesos_to_review)
        update_spreadsheet_data(summary_df, sheet_name=SUMMARY_SHEET_NAME)

        logger.info("Sending email notification")
        send_email_notification(
            subject=EMAIL_SUBJECT_TEMPLATE,
            message=format_notification_message(procesos_to_notify, procesos_to_impulsar, procesos_to_review),
            recipient_email=os.getenv("EMAIL_RECIPIENT")
        )
        
        logger.info("Notification sent")
    logger.info("Workflow completed successfully")
    return "Completed"