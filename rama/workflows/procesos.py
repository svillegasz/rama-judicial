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
        
    total_procesos = len(procesos_df)
    
    for index, proceso in procesos_df.iterrows():
        progress = f"[{index + 1}/{total_procesos}]"
        radicado = proceso[RADICADO_COLUMN]
        
        try:        
            logger.info(f"{progress} Processing proceso: {radicado}")
            
            # Get the latest actuacion from API
            data = get_latest_actuacion(radicado)
            
            # Check if the process is older than 6 months and needs to be impulsado
            if check_fecha_older_than_months(data[FECHA_ACTUACION_FIELD], 6):
                logger.info(f"{progress} ⚠️  Proceso {radicado} requires impulso (>6 months old)")
                procesos_to_impulsar.append({radicado: data})
            elif check_fecha(data[FECHA_ACTUACION_FIELD], 7):
                # Check if there's a recent update (within last 7 days)
                logger.info(f"{progress} ✓ Proceso {radicado} has recent update")
                procesos_to_notify.append({radicado: data})            
            else:
                logger.info(f"{progress} - Proceso {radicado} has no recent updates")
        except Exception as e:
            procesos_to_review.append({radicado: str(e)})
            logger.error(f"{progress} ✗ Error processing proceso {radicado}: {e}")

    # Log final summary
    logger.info("=" * 60)
    logger.info("PROCESSING SUMMARY")
    logger.info(f"Total procesos checked: {total_procesos}")
    logger.info(f"Recent updates found: {len(procesos_to_notify)}")
    logger.info(f"Require impulso (>6 months): {len(procesos_to_impulsar)}")
    logger.info(f"Failed to process: {len(procesos_to_review)}")
    logger.info("=" * 60)
    
    if not procesos_to_notify and not procesos_to_impulsar and not procesos_to_review:
        logger.info("No processes require notification")
    else:
        logger.info("Generating summary report and sending notifications")
        
        summary_df = generate_summary_report(procesos_to_notify, procesos_to_impulsar, procesos_to_review)
        update_spreadsheet_data(summary_df, sheet_name=SUMMARY_SHEET_NAME)

        send_email_notification(
            subject=EMAIL_SUBJECT_TEMPLATE,
            message=format_notification_message(
                procesos_to_notify, 
                procesos_to_impulsar, 
                procesos_to_review,
                total_procesos
            ),
            recipient_email=os.getenv("EMAIL_RECIPIENT")
        )
        
        logger.info("✓ Notifications sent successfully")
    
    logger.info("Workflow completed successfully")
    return "Completed"