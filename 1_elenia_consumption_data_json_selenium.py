import sys
import time
import random
import json
import os
import urllib
from urllib.parse import unquote
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
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

def fetch_consumption_data():
    # Load environment variables from .env file
    load_dotenv()

    username = os.getenv('ELENIA_USERNAME')
    password = os.getenv('ELENIA_PASSWORD')

    if not username or not password:
        logger.error("USERNAME and PASSWORD must be set in the .env file.")
        sys.exit(1)

    downloadDir = f"{os.getcwd()}//downloads//"
    
    # Set Preferences.
    preferences = {"download.default_directory": downloadDir,
                   "download.prompt_for_download": False,
                   "directory_upgrade": True,
                   "safebrowsing.enabled": True}
    chromeOptions = webdriver.ChromeOptions()
    chromeOptions.add_argument("--window-size=1480x560")
    chromeOptions.add_experimental_option("prefs", preferences)

    # Website URL
    auth_url = 'https://idm.asiakas.elenia.fi/'

    # Create a new Chrome browser instance
    driver = webdriver.Chrome(options=chromeOptions)

    # Get the User-Agent from the Selenium WebDriver
    user_agent = driver.execute_script("return navigator.userAgent;")

    # Navigate to the authentication page
    driver.get(auth_url)
    delay = 3  # seconds
    try:
        myElem = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'signin-email')))
        logger.info("Page is ready!")
    except TimeoutException:
        logger.warning("Loading took too much time!")

    # Find cookie button and click it "allow all cookies"
    cookie_button = driver.find_element(By.XPATH, '//button[@id="CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"]')
    cookie_button.click()

    # Find the username and password input fields
    username_element = driver.find_element(By.XPATH, "//input[@id='signin-email']")
    password_element = driver.find_element(By.XPATH, "//input[@id='password']")

    # Create an ActionChains object
    actions = ActionChains(driver)

    # Login process
    logger.info("Logging in...")
    actions.move_to_element(username_element).click().send_keys(username).send_keys(Keys.TAB).send_keys(password).send_keys(Keys.TAB).send_keys(Keys.ENTER).perform()

    time.sleep(5)
    ainalab_button = driver.find_element(By.XPATH, '//button[@aria-label="Elenia Aina"]')
    ainalab_button.click()

    time.sleep(2)

    cookies = driver.get_cookies()

    # Extract user data and access token from cookies
    user_data = next((json.loads(unquote(cookie['value'])) for cookie in cookies if cookie['name'].endswith('.userData')), None)
    access_token = next((cookie['value'] for cookie in cookies if cookie['name'].endswith('.accessToken')), None)

    if user_data:
        sub_value = next((attr['Value'] for attr in user_data['UserAttributes'] if attr['Name'] == 'sub'), None)
        logger.info(f"User sub value: {sub_value}" if sub_value else "Sub value not found in user data")
    else:
        logger.warning("User data cookie not found")

    if access_token:
        logger.info("Access Token: found")
    else:
        logger.warning("Access Token not found")

    bearer_token = access_token
    logger.info(f"Bearer token retrieved: {'Success' if bearer_token else 'Failed'}")

    if not bearer_token:
        logger.error("Failed to retrieve bearer token. Exiting.")
        driver.quit()
        sys.exit(1)

    logger.info("Fetching consumption data from API")

    # Set up headers with bearer token
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json",
        "User-Agent": user_agent,
    }

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
        driver.quit()
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
        driver.quit()
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
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            logger.info("Successfully fetched consumption data")
            with open("downloads/consumption_data.json", "w") as outfile:
                json.dump(data, outfile, indent=2)
            logger.info("Saved consumption data to consumption_data.json")
        else:
            logger.error(f"Failed to fetch data. Status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.exception(f"An error occurred: {e}")

    driver.quit()

def main():
    logger.info("Starting consumption data fetch process")
    fetch_consumption_data()
    logger.info("Consumption data fetch process completed")

if __name__ == "__main__":
    main()