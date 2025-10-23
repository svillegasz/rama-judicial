import os
import pandas as pd
from prefect import flow
import logging

from rama.tasks.google_drive import get_spreadsheet_data, update_spreadsheet_data 
from rama.tasks.api_client import get_latest_actuacion
from rama.tasks.notifications import generate_summary_report, send_email_notification, format_notification_message
from rama.utils.constants import (
    PROCESOS_SHEET_NAME,
    RADICADO_COLUMN,
    SUMMARY_SHEET_NAME,
    EMAIL_SUBJECT_TEMPLATE,
    check_fecha,
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
    fetch latest actuacion from API, and send notifications
    when certain conditions are met.
    """  
    procesos_df = get_spreadsheet_data(sheet_name=PROCESOS_SHEET_NAME)
    procesos_to_notify = []
    procesos_to_impulsar = []
    procesos_to_review = []
    
    # Log the start of the process
    logger.info("Starting process review workflow")
    logger.info(f"Found {len(procesos_df)} processes to check")
        
    for index, proceso in procesos_df.iterrows():
        try:        
            radicado = proceso[RADICADO_COLUMN]
            logger.info(f"Processing process {radicado}")
            
            # Get the latest actuacion from API
            data = get_latest_actuacion(radicado)
            
            # Check if the process is older than 6 months and needs to be impulsado
            if check_fecha_older_than_months(data[FECHA_ACTUACION_FIELD], 6):
                logger.info(f"Process {radicado} is older than 6 months, adding to impulsar list")
                procesos_to_impulsar.append({radicado: data})
            elif check_fecha(data[FECHA_ACTUACION_FIELD], 7):
                # Check if there's a recent update (within last 7 days)
                logger.info(f"Process {radicado} has recent update, adding to notification list")
                procesos_to_notify.append({radicado: data})            
            else:
                logger.info(f"Process {radicado} did not meet notification criteria")
        except Exception as e:
            procesos_to_review.append({radicado: str(e)})
            logger.error(f"Error processing process {radicado}: {e}")

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