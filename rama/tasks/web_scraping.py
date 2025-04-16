import requests
from bs4 import BeautifulSoup
from prefect import task
from rama.utils.constants import FECHA_ACTUACION_FIELD, Selector, PAYLOAD_TEMPLATE, format_payload_template, RAMA_HEADERS, extract_session_cookie, ASP_NET_SESSION_ID

@task
def fetch_html_content(url):
    """
    Fetch HTML content from a given URL
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Extract and store ASP.NET_SessionId if present
        session_id = extract_session_cookie(response)
        if session_id:
            # Update the cookie header with the new session ID
            RAMA_HEADERS['Cookie'] = f"{ASP_NET_SESSION_ID}={session_id}"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except Exception as e:
        raise Exception(f"Failed to fetch HTML content from {url}: {str(e)}")
    
@task
def submit_payload(url, payload):
    """
    Submit payload to RAMA
    
    Args:
        payload: Dictionary with payload
        
    Returns:
        BeautifulSoup object
    """
    try:
        data = format_payload_template(payload)
        response = requests.post(url, data=data, headers=RAMA_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except Exception as e:
        raise Exception(f"Failed to submit payload: {str(e)}")

@task
def extract_data_from_page(soup, data_selectors: list[Selector]):
    """
    Extract specific data from a parsed HTML page
    
    Args:
        soup: BeautifulSoup object
        data_selectors: Dictionary mapping field names to CSS selectors
        
    Returns:
        Dictionary with extracted data
    """
    result = {}
    try:
        for selector in data_selectors:
            element = soup.select_one(selector.css_selector)
            if selector.result_type == "value":
                result[selector.name] = element.get("value")
            elif selector.result_type == "text":
                result[selector.name] = element.get_text(strip=True)
        return result
    except Exception as e:
        raise Exception(f"Failed to extract data from page: {str(e)}")

@task
def validate_data(data, validation_rules):
    """
    Validate extracted data based on rules
    
    Args:
        data: Dictionary with extracted data
        validation_rules: Dictionary with field names and validation functions
        
    Returns:
        Tuple (is_valid, validation_messages)
    """
    validation_messages = []
    is_valid = True
    
    try:
        for field, validation_fn in validation_rules.items():
            if field in data:
                field_valid = validation_fn(data[field])
                if not field_valid:
                    is_valid = False
                    validation_messages.append(f"Validation failed for field '{field}'")
            else:
                is_valid = False
                validation_messages.append(f"Missing required field '{field}'")
        
        return is_valid, validation_messages
    except Exception as e:
        raise Exception(f"Error during data validation: {str(e)}") 