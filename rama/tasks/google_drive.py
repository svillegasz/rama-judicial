import pandas as pd
import os
import io
from googleapiclient.discovery import build

from prefect import task

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

@task
def get_spreadsheet_data(sheet_name="Sheet1"):
    """
    Fetch data from a public Google Spreadsheet
    
    Args:
        sheet_name: Name of the sheet to fetch (default: "Sheet1")
        
    Returns:
        pandas DataFrame with the spreadsheet data
    """
    try:
        # Build the Sheets API service
        service = build('sheets', 'v4')
        
        # Call the Sheets API to get the data
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name
        ).execute()
        
        # Extract values from the result
        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame()
        
        # Convert to DataFrame (first row as header)
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        
        return df
    except Exception as e:
        raise Exception(f"Failed to fetch spreadsheet data from sheet '{sheet_name}': {str(e)}")

@task
def update_spreadsheet_data(df, sheet_name="Sheet1"):
    """
    Update a specific sheet in a Google Spreadsheet using Sheets API v4
    
    Args:
        df: pandas DataFrame with the new data to upload
        sheet_name: Name of the sheet to update (default: "Sheet1")
        
    Returns:
        Boolean indicating success
    """
    try:
        # Build the Sheets API service
        service = build('sheets', 'v4')
        
        # Convert DataFrame to values list
        values = [df.columns.tolist()]  # Header row
        values.extend(df.values.tolist())  # Data rows
        
        # First clear the sheet
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name,
        ).execute()
        
        # Then update with new data
        body = {
            'values': values
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True
    except Exception as e:
        raise Exception(f"Failed to update spreadsheet data in sheet '{sheet_name}': {str(e)}")

