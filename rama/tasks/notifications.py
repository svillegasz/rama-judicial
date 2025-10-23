import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from prefect import task
import logging
import os

from rama.tasks.google_drive import SPREADSHEET_ID
from rama.utils.constants import ACTUACION_FIELD, FECHA_ACTUACION_FIELD, format_date_for_display
from rama.utils.logging_utils import get_logger

logger = get_logger("tasks.notifications")


@task
def send_email_notification(subject, message, recipient_email, 
                           sender_email=None, smtp_server=None, smtp_port=None, 
                           smtp_username=None, smtp_password=None):
    """
    Send an email notification
    
    Args:
        subject: Email subject
        message: Email body content
        recipient_email: Email address of the recipient
        sender_email: Email address of the sender (if None, requires env variable)
        smtp_server: SMTP server address (if None, requires env variable)
        smtp_port: SMTP server port (if None, requires env variable)
        smtp_username: SMTP username (if None, requires env variable)
        smtp_password: SMTP password (if None, requires env variable)
    """
    
    sender = sender_email or os.environ.get("SMTP_USERNAME")
    server = smtp_server or os.environ.get("SMTP_SERVER")
    port = smtp_port or int(os.environ.get("SMTP_PORT", 587))
    username = smtp_username or os.environ.get("SMTP_USERNAME")
    password = smtp_password or os.environ.get("SMTP_PASSWORD")
    
    # Validate required parameters
    if not all([sender, server, port, username, password, recipient_email]):
        missing = []
        if not sender: missing.append("sender_email")
        if not server: missing.append("smtp_server")
        if not port: missing.append("smtp_port")
        if not username: missing.append("smtp_username")
        if not password: missing.append("smtp_password")
        if not recipient_email: missing.append("recipient_email")
        
        raise ValueError(f"Missing required email parameters: {', '.join(missing)}")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Attach message body
        msg.attach(MIMEText(message, 'html'))
        
        # Connect to server and send
        with smtplib.SMTP(server, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
            
        return True
    except Exception as e:
        raise Exception(f"Failed to send email notification: {str(e)}") 
    
@task
def format_notification_message(procesos_to_notify, procesos_to_impulsar, procesos_to_review):
    """Format the notification message with the process data
    
    Args:
        procesos_to_notify: List of dictionaries, each containing a single key-value pair
                           where key is process_id and value is process data
        procesos_to_impulsar: List of dictionaries, each containing a single key-value pair
                           where key is process_id and value is process data for processes older than 6 months
        procesos_to_review: List of dictionaries, each containing a single key-value pair
                           where key is process_id and value is error message
    
    Returns:
        HTML formatted message string
    """    
    # Extract notification data from list of dictionaries
    notification_items = []
    for proceso_dict in procesos_to_notify:
        for process_id, data in proceso_dict.items():
            fecha = format_date_for_display(data.get(FECHA_ACTUACION_FIELD, ''))
            notification_items.append(f'<li><strong>{process_id}:</strong> {data[ACTUACION_FIELD]} - {fecha}</li>')
    
    # Extract impulsar data from list of dictionaries
    impulsar_items = []
    if procesos_to_impulsar:
        for proceso_dict in procesos_to_impulsar:
            for process_id, data in proceso_dict.items():
                fecha = format_date_for_display(data.get(FECHA_ACTUACION_FIELD, ''))
                impulsar_items.append(f'<li><strong>{process_id}:</strong> {data[ACTUACION_FIELD]} - {fecha}</li>')
    
    # Extract review data from list of dictionaries
    review_items = []
    if procesos_to_review:
        for proceso_dict in procesos_to_review:
            for process_id, error in proceso_dict.items():
                review_items.append(f'<li><strong>{process_id}:</strong> {error}</li>')
    
    return f"""
    <html>
    <body>
        <h2>Notificación de Rama Judicial</h2>
        {f'''<p>Se ha detectado una actualización importante en los siguientes procesos:</p>
        <ul>
            {''.join(notification_items)}
        </ul>
        <br>''' if notification_items else ''}
        {f'''<p>Se requiere impulsar los siguientes procesos:</p>
        <ul>
            {''.join(impulsar_items)}
        </ul>
        <br>''' if impulsar_items else ''}
        {f'''<p>Se ha detectado fallos al procesar los siguientes procesos:</p>
        <ul>
            {''.join(review_items)}
        </ul>''' if review_items else ''}
        <p>Ver detalles completos: <a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit?usp=sharing">Link al reporte</a></p>
    </body>
    </html>
    """

@task
def generate_summary_report(procesos_to_notify, procesos_to_impulsar, procesos_to_review):
    # Create a dataframe for processes with updates
    if procesos_to_notify:
        notify_data = []
        for proceso_dict in procesos_to_notify:
            for process_id, data in proceso_dict.items():
                fecha = format_date_for_display(data.get(FECHA_ACTUACION_FIELD, ""))
                notify_data.append({
                    "Proceso con novedad": process_id,
                    "Fecha de Actuacion": fecha,
                    "Actuacion": data.get(ACTUACION_FIELD, "")
                })
        notify_df = pd.DataFrame(notify_data)
    else:
        notify_df = pd.DataFrame(columns=["Proceso con novedad", "Fecha de Actuacion", "Actuacion"])
    
    # Create a dataframe for processes to impulsar (older than 6 months)
    if procesos_to_impulsar:
        impulsar_data = []
        for proceso_dict in procesos_to_impulsar:
            for process_id, data in proceso_dict.items():
                fecha = format_date_for_display(data.get(FECHA_ACTUACION_FIELD, ""))
                impulsar_data.append({
                    "Proceso a impulsar": process_id,
                    "Fecha de Actuacion": fecha,
                    "Actuacion": data.get(ACTUACION_FIELD, "")
                })
        impulsar_df = pd.DataFrame(impulsar_data)
    else:
        impulsar_df = pd.DataFrame(columns=["Proceso a impulsar", "Fecha de Actuacion", "Actuacion"])
    
    # Create a dataframe for failed processes
    if procesos_to_review:
        review_data = []
        for proceso_dict in procesos_to_review:
            for process_id, error in proceso_dict.items():
                review_data.append({
                    "Procesos fallidos": process_id,
                    "Error": error
                })
        review_df = pd.DataFrame(review_data)
    else:
        review_df = pd.DataFrame(columns=["", ""])
    
    # Combine the dataframes with an empty column in between each
    max_rows = max(len(notify_df), len(impulsar_df), len(review_df))
    empty_df1 = pd.DataFrame({"": [""] * max_rows})
    empty_df2 = pd.DataFrame({" ": [""] * max_rows})
    
    result_df = pd.concat([notify_df, empty_df1, impulsar_df, empty_df2, review_df], axis=1)
    result_df = result_df.fillna("")
    
    logger.info(f"Created summary dataframe with {len(notify_df)} processes with updates, {len(impulsar_df)} processes to impulsar, and {len(review_df)} failed processes")
    return result_df
