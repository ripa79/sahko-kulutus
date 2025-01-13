import sys
import time
import json
import os
import requests
from dotenv import load_dotenv
import logging

# ensure downloads folder exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def get_cognito_token(username, password):
    cognito_url = "https://cognito-idp.eu-west-1.amazonaws.com/"
    headers = {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
    }
    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": "k4s2pnm04536t1bm72bdatqct",
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password
        },
        "ClientMetadata": {}
    }
    
    response = requests.post(cognito_url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['AuthenticationResult']['AccessToken']
    else:
        logger.error(f"Authentication failed: {response.text}")
        return None

def make_request_with_retry(method, url, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code == 504:
                wait_time = 2 ** attempt  # exponential backoff
                logger.warning(f"Got 504 error, retry attempt {attempt + 1}/{max_retries} after {wait_time} seconds")
                time.sleep(wait_time)
                continue
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            logger.warning(f"Request failed, retry attempt {attempt + 1}/{max_retries} after {wait_time} seconds: {e}")
            time.sleep(wait_time)
    return None

def fetch_consumption_data():
    # Load environment variables from .env file
    load_dotenv()

    username = os.getenv('ELENIA_USERNAME')
    password = os.getenv('ELENIA_PASSWORD')

    if not username or not password:
        logger.error("USERNAME and PASSWORD must be set in the .env file.")
        sys.exit(1)

    # Get bearer token from Cognito
    bearer_token = get_cognito_token(username, password)
    if not bearer_token:
        logger.error("Failed to retrieve bearer token. Exiting.")
        sys.exit(1)

    logger.info("Bearer token retrieved successfully")

    # Set up headers with bearer token
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Extract sub from bearer token (assuming it's in the token payload)
    import base64
    token_parts = bearer_token.split('.')
    if len(token_parts) > 1:
        payload = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)).decode('utf-8'))
        sub_value = payload.get('sub')
        logger.info(f"Extracted sub value from token: {sub_value}")
    else:
        logger.error("Could not extract sub value from token")
        sys.exit(1)

    # Fetch customer metadata
    metadata_url = f"https://api.asiakas.aina-extranet.com/idm/customerMetadata?sub={sub_value}"
    try:
        response = requests.get(metadata_url, headers=headers)
        response.raise_for_status()
        metadata = response.json()
        customer_id = metadata.get("data", {}).get("customer_ids", [])[0]
        logger.info(f"Customer ID retrieved: {customer_id}")
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching customer metadata: {e}")
        sys.exit(1)

    # Fetch customer account metadata
    customer_metadata_url = f"https://api.asiakas.aina-extranet.com/customer/customers?customerId[]={customer_id}"
    try:
        response = requests.get(customer_metadata_url, headers=headers)
        response.raise_for_status()
        metadata = response.json()
        metering_point_id = metadata['data'][0]['contracts'][0]['meteringPoint']['meteringPointId']
        logger.info(f"Metering Point ID retrieved: {metering_point_id}")
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching customer account metadata: {e}")
        sys.exit(1)

    # Fetch consumption data
    url = f"https://api.asiakas.aina-extranet.com/consumption/consumption/energy/{metering_point_id}"
    params = {
        "customerId": customer_id,
        "end": "2025-01-01T00:00:00+02:00",
        "resolution": "hour",
        "netted": "true",
        "start": "2024-01-01T00:00:00+02:00"
    }
    headers["Content-Type"] = "application/json"
    headers["X-Amz-Date"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    try:
        response = make_request_with_retry('GET', url, params=params, headers=headers)
        if response and response.status_code == 200:
            data = response.json()
            logger.info("Successfully fetched consumption data")
            with open("downloads/consumption_data.json", "w") as outfile:
                json.dump(data, outfile, indent=2)
            logger.info("Saved consumption data to consumption_data.json")
        else:
            logger.error(f"Failed to fetch data. Status code: {response.status_code if response else 'No response'}")
            if response:
                logger.error(f"Response content: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.exception(f"An error occurred after all retry attempts: {e}")

def main():
    logger.info("Starting consumption data fetch process")
    fetch_consumption_data()
    logger.info("Consumption data fetch process completed")

if __name__ == "__main__":
    main()