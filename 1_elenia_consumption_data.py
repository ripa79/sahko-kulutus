# 	https://public.sgp-prod.aws.elenia.fi/api/gen/customer_data_and_token
#   https://public.sgp-prod.aws.elenia.fi/api/gen/meter_reading?customer_ids=7191131&gsrn=643006966022748876&day=2025-01-01
#   https://public.sgp-prod.aws.elenia.fi/api/gen/meter_reading_yh?gsrn=643006966035502953&customer_ids=7191131&year=2025

import sys
import time
import json
import os
import requests
from dotenv import load_dotenv
import logging
import argparse

# ensure downloads folder exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Set up argument parser
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args = parser.parse_args()

# Set up logging
logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
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
    
    logger.debug(f"Making Cognito auth request to: {cognito_url}")
    logger.debug(f"Auth request headers: {headers}")
    logger.debug(f"Auth request payload: {json.dumps({**payload, 'AuthParameters': {'USERNAME': username, 'PASSWORD': '[REDACTED]'}})}")
    
    response = requests.post(cognito_url, headers=headers, json=payload)
    logger.debug(f"Cognito response status code: {response.status_code}")
    
    if response.status_code == 200:
        logger.debug("Successfully retrieved auth token")
        return response.json()['AuthenticationResult']['AccessToken']
    else:
        logger.error(f"Authentication failed: {response.text}")
        return None

def make_request_with_retry(method, url, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            logger.debug(f"Making {method} request to: {url}")
            if 'params' in kwargs:
                logger.debug(f"Request params: {kwargs['params']}")
            if 'headers' in kwargs:
                sanitized_headers = {k: v for k, v in kwargs['headers'].items() if k.lower() != 'authorization'}
                logger.debug(f"Request headers: {sanitized_headers}")
            
            response = requests.request(method, url, **kwargs)
            logger.debug(f"Response status code: {response.status_code}")
            
            if response.status_code == 504:
                wait_time = 2 ** attempt  # exponential backoff
                logger.warning(f"Got 504 error, retry attempt {attempt + 1}/{max_retries} after {wait_time} seconds")
                logger.debug(f"Response content: {response.text}")
                time.sleep(wait_time)
                continue
                
            if response.status_code >= 400:
                logger.error(f"Request failed with status {response.status_code}")
                logger.error(f"Response content: {response.text}")
                
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Final request attempt failed: {str(e)}")
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
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://ainalab.aws.elenia.fi/",
        "Origin": "https://ainalab.aws.elenia.fi",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
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

    # Fetch customer metadata using Cognito token
    metadata_url = f"https://public.sgp-prod.aws.elenia.fi/api/gen/customer_data_and_token"
    logger.debug(f"Fetching customer metadata from: {metadata_url}")
    try:
        response = requests.get(metadata_url, headers=headers)
        logger.debug(f"Metadata response status code: {response.status_code}")
        response.raise_for_status()
        metadata = response.json()
        logger.debug(f"Successfully parsed metadata response")
        
        # Save metadata to file
        metadata_file = "downloads/metadata.json"
        with open(metadata_file, "w", encoding='utf-8') as outfile:
            json.dump(metadata, outfile, indent=2, ensure_ascii=False)
        logger.info(f"Saved metadata to {metadata_file}")
        
        # Extract token from metadata
        api_token = metadata.get('token')
        if not api_token:
            logger.error("No token found in metadata response")
            sys.exit(1)
        
        # Update headers with the new token
        headers['Authorization'] = f"Bearer {api_token}"
        
        # Extract customer ID (first key in customer_datas)
        customer_id = next(iter(metadata.get('customer_datas', {})))
        
        # Extract customer data using the customer ID
        customer_data = metadata['customer_datas'][customer_id]
        
        # Find consumption and production GSRNs
        consumption_gsrn = None
        production_gsrn = None
        
        for meteringpoint in customer_data.get('meteringpoints', []):
            if 'additional_information' in meteringpoint:
                if meteringpoint['additional_information'] == 'Liittymällä tuotannon käyttöpaikka.':
                    # This is the consumption point
                    consumption_gsrn = meteringpoint.get('gsrn')
                # Check if this is the production point by looking for the virtual device
                if meteringpoint.get('device', {}).get('name') == 'Tuotannon virtuaalilaite':
                    production_gsrn = meteringpoint.get('gsrn')
        
        logger.info(f"GSRN for consumption: {consumption_gsrn}")
        logger.info(f"GSRN for production: {production_gsrn}")
        
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching customer metadata: {e}")
        logger.debug(f"Failed response content: {getattr(e.response, 'text', 'No response content')}")
        sys.exit(1)

    # Update the data fetching for both consumption and production
    current_year = os.getenv('YEAR')
    
    for gsrn, data_type in [(consumption_gsrn, "consumption"), (production_gsrn, "production")]:
        if not gsrn:
            logger.warning(f"No GSRN found for {data_type}")
            continue
            
        url = f"https://public.sgp-prod.aws.elenia.fi/api/gen/meter_reading_yh"
        params = {
            "gsrn": gsrn,
            "customer_ids": customer_id,
            "year": current_year
        }

        try:
            response = make_request_with_retry('GET', url, params=params, headers=headers)
            if response and response.status_code == 200:
                data = response.json()
                
                # Add data validation
                for month in data.get('months', []):
                    if month.get('hourly_values'):
                        first_timestamp = month['hourly_values'][0]['t']
                        last_timestamp = month['hourly_values'][-1]['t']
                        count = len(month['hourly_values'])
                        logger.info(f"{data_type} data for month {month['month']}: {count} records from {first_timestamp} to {last_timestamp}")
                    
                logger.info(f"Successfully fetched {data_type} data")
                filename = f"downloads/{data_type}_data.json"
                with open(filename, "w", encoding='utf-8') as outfile:
                    json.dump(data, outfile, indent=2, ensure_ascii=False)
                logger.info(f"Saved {data_type} data to {filename}")
                
                # Verify data completeness
                total_hours = sum(len(month.get('hourly_values', [])) for month in data.get('months', []))
                logger.info(f"Total hours of data for {data_type}: {total_hours}")
                
            else:
                logger.error(f"Failed to fetch {data_type} data. Status code: {response.status_code if response else 'No response'}")
                if response:
                    logger.error(f"Response content: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.exception(f"An error occurred while fetching {data_type} data: {e}")

def main():
    logger.info("Starting consumption data fetch process")
    fetch_consumption_data()
    logger.info("Consumption data fetch process completed")

if __name__ == "__main__":
    main()