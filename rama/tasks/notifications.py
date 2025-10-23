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
def format_notification_message(procesos_to_notify, procesos_to_impulsar, procesos_to_review, total_procesos):
    """Format the notification message with the process data and summary statistics
    
    Args:
        procesos_to_notify: List of dictionaries with processes that have recent updates
        procesos_to_impulsar: List of dictionaries with processes requiring impulso (>6 months)
        procesos_to_review: List of dictionaries with processes that failed processing
        total_procesos: Total number of processes checked
    
    Returns:
        HTML formatted message string with summary and detailed lists
    """    
    # Extract notification data from list of dictionaries
    notification_items = []
    for proceso_dict in procesos_to_notify:
        for process_id, data in proceso_dict.items():
            fecha = format_date_for_display(data.get(FECHA_ACTUACION_FIELD, ''))
            actuacion = data.get(ACTUACION_FIELD, '')
            notification_items.append(
                f'<li><strong>{process_id}</strong><br/>'
                f'<span style="color: #666; font-size: 0.9em;">{actuacion} - {fecha}</span></li>'
            )
    
    # Extract impulsar data from list of dictionaries
    impulsar_items = []
    if procesos_to_impulsar:
        for proceso_dict in procesos_to_impulsar:
            for process_id, data in proceso_dict.items():
                fecha = format_date_for_display(data.get(FECHA_ACTUACION_FIELD, ''))
                actuacion = data.get(ACTUACION_FIELD, '')
                impulsar_items.append(
                    f'<li><strong>{process_id}</strong><br/>'
                    f'<span style="color: #666; font-size: 0.9em;">{actuacion} - {fecha}</span></li>'
                )
    
    # Extract review data from list of dictionaries
    review_items = []
    if procesos_to_review:
        for proceso_dict in procesos_to_review:
            for process_id, error in proceso_dict.items():
                review_items.append(
                    f'<li><strong>{process_id}</strong><br/>'
                    f'<span style="color: #d32f2f; font-size: 0.9em;">{error}</span></li>'
                )
    
    # Calculate summary statistics
    processed_successfully = total_procesos - len(procesos_to_review)
    
    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h2 {{
                color: #1976d2;
                border-bottom: 3px solid #1976d2;
                padding-bottom: 10px;
            }}
            .summary-box {{
                background-color: #f5f5f5;
                border-left: 4px solid #1976d2;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .summary-box h3 {{
                margin-top: 0;
                color: #1976d2;
            }}
            .stat-row {{
                display: flex;
                justify-content: space-between;
                padding: 5px 0;
                border-bottom: 1px solid #ddd;
            }}
            .stat-label {{
                font-weight: bold;
            }}
            .section {{
                margin: 30px 0;
            }}
            .section h3 {{
                color: #424242;
                background-color: #e3f2fd;
                padding: 10px;
                border-radius: 4px;
            }}
            .warning-section h3 {{
                background-color: #fff3e0;
                color: #e65100;
            }}
            .error-section h3 {{
                background-color: #ffebee;
                color: #c62828;
            }}
            ul {{
                list-style-type: none;
                padding-left: 0;
            }}
            li {{
                padding: 10px;
                margin: 5px 0;
                background-color: #fafafa;
                border-left: 3px solid #2196f3;
                border-radius: 3px;
            }}
            .warning-section li {{
                border-left-color: #ff9800;
            }}
            .error-section li {{
                border-left-color: #f44336;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 2px solid #ddd;
                text-align: center;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #1976d2;
                color: white !important;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h2>📋 Notificación de Rama Judicial</h2>
        
        <div class="summary-box">
            <h3>Resumen de Procesamiento</h3>
            <div class="stat-row">
                <span class="stat-label">Total de procesos revisados:</span>
                <span>{total_procesos}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Procesados exitosamente:</span>
                <span>{processed_successfully}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Con actualizaciones recientes:</span>
                <span style="color: #2e7d32; font-weight: bold;">{len(procesos_to_notify)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Requieren impulso (>6 meses):</span>
                <span style="color: #f57c00; font-weight: bold;">{len(procesos_to_impulsar)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Errores al procesar:</span>
                <span style="color: #c62828; font-weight: bold;">{len(procesos_to_review)}</span>
            </div>
        </div>
        
        {f'''<div class="section">
            <h3>✅ Actualizaciones Recientes (últimos 7 días)</h3>
            <p>Los siguientes procesos han tenido actualizaciones importantes:</p>
            <ul>
                {''.join(notification_items)}
            </ul>
        </div>''' if notification_items else ''}
        
        {f'''<div class="section warning-section">
            <h3>⚠️ Procesos que Requieren Impulso</h3>
            <p>Los siguientes procesos no han tenido movimiento en más de 6 meses y requieren acción:</p>
            <ul>
                {''.join(impulsar_items)}
            </ul>
        </div>''' if impulsar_items else ''}
        
        {f'''<div class="section error-section">
            <h3>❌ Errores al Procesar</h3>
            <p>No se pudieron procesar los siguientes procesos:</p>
            <ul>
                {''.join(review_items)}
            </ul>
        </div>''' if review_items else ''}
        
        <div class="footer">
            <p>Para ver el reporte completo y más detalles:</p>
            <a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit?usp=sharing" class="button">
                Ver Reporte Completo
            </a>
        </div>
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
