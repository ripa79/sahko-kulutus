from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os
import sys
from selenium.webdriver.common.action_chains import ActionChains
import random
import requests
import json
import urllib
from urllib.parse import urlencode, unquote

if len(sys.argv) != 3:
    print("Usage: python script.py <username> <password>")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

downloadDir = f"{os.getcwd()}//downloads//"
# Make sure path exists.
# Path(downloadDir).mkdir(parents=True, exist_ok=True)
# output file will be YYYY.csv (for example 2023.csv)

# Set Preferences.
preferences = {"download.default_directory": downloadDir,
               "download.prompt_for_download": False,
               "directory_upgrade": True,
               "safebrowsing.enabled": True}
chromeOptions = webdriver.ChromeOptions()
chromeOptions.add_argument("--window-size=1480x560")
#chromeOptions.add_argument("--headless")
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
    print("Page is ready!")
except TimeoutException:
    print("Loading took too much time!")

# Find cookie button and click it "allow all cookies"
cookie_button = driver.find_element(By.XPATH, '//button[@id="CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"]')
cookie_button.click()

# Find the username input field
username_element = driver.find_element(By.XPATH, "//input[@id='signin-email']")
password_element = driver.find_element(By.XPATH, "//input[@id='password']")
#print(password_element)

# Create an ActionChains object
actions = ActionChains(driver)

# Click on the username field
print("Clicking on username field")
actions.move_to_element(username_element).click().perform()
time.sleep(random.uniform(0.5, 1.0))

# Type the username in one go
print("Filling in the username")
actions.send_keys(username).perform()
time.sleep(random.uniform(0.5, 1.0))

# Press TAB to move to the next field (should be password)
print("Pressing TAB to move to password field")
actions.send_keys(Keys.TAB).perform()
time.sleep(random.uniform(0.5, 1.0))

# Check if we're on the password field
active_element = driver.switch_to.active_element
if active_element.get_attribute('id') == 'password':
    print("Successfully moved to password field")
    # Type the password
    print("Filling in the password")
    actions.send_keys(password).perform()
else:
    print("Failed to move to password field")
    # Here you could implement a fallback method or error handling

# Press TAB again to move to the login button
actions.send_keys(Keys.TAB).perform()
time.sleep(random.uniform(0.5, 1.0))

# Check if we're on the login button
active_element = driver.switch_to.active_element
if active_element.get_attribute('type') == 'submit':
    print("Successfully moved to login button")
    # Press ENTER to submit the form
    actions.send_keys(Keys.ENTER).perform()
else:
    print("Failed to move to login button")
    # Here you could implement a fallback method or error handling

time.sleep(5)
ainalab_button = driver.find_element(By.XPATH, '//button[@aria-label="Elenia Aina"]')

#press the button
ainalab_button.click()

time.sleep(2)

cookies = driver.get_cookies()

# lets get the user name from cookie that ends userData

user_data = None
for cookie in cookies:
    if cookie['name'].endswith('.userData'):
        #print(cookie['value'])
        # url decode the value
        user_data = json.loads(urllib.parse.unquote(cookie['value']))
        break

if user_data:
    # Extract the 'sub' value from UserAttributes
    sub_value = next((attr['Value'] for attr in user_data['UserAttributes'] if attr['Name'] == 'sub'), None)
    
    if sub_value:
        print(f"User sub value: {sub_value}")
    else:
        print("Sub value not found in user data")
else:
    print("User data cookie not found")


# get the access token from the cookies it ends accessToken
access_token = None
for cookie in cookies:
    if cookie['name'].endswith('.accessToken'):
        access_token = cookie['value']
        break

# Print the access token
if access_token:
    print("Access Token: found")
else:
    print("Access Token not found")

# Now let's get the bearer token after we've navigated to the protected resource
print("Retrieving bearer token...")
bearer_token = access_token
print(f"Bearer token retrieved: {'Success' if bearer_token else 'Failed'}")

if not bearer_token:
    print("Failed to retrieve bearer token. Exiting.")
    driver.quit()
    sys.exit(1)

print("Fetching consumption data from API")

# Set up headers with bearer token
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Accept": "application/json"
}

# use the sub value in get request to https://api.asiakas.aina-extranet.com/idm/customerMetadata?sub=
metadata_url = f"https://api.asiakas.aina-extranet.com/idm/customerMetadata?sub={sub_value}"

try:
    # Make the GET request to customerMetadata
    response = requests.get(metadata_url, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors

    # Parse the JSON response
    metadata = response.json()

    # Extract the first customer_id from customer_ids
    customer_ids = metadata.get("data", {}).get("customer_ids", [])
    if customer_ids:
        customer_id = customer_ids[0]
        print(f"Customer ID retrieved: {customer_id}")
    else:
        print("No customer IDs found in metadata response")

except requests.exceptions.RequestException as e:
    print(f"Error fetching customer metadata: {e}")

headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Accept": "*/*",
    "content-type": "application/json",
    "User-Agent": user_agent,
    "Origin": "https://asiakas.elenia.fi",
}

# fetch https://api.asiakas.aina-extranet.com/customer/customers?customerId[]=

customer_metadata_url = f"https://api.asiakas.aina-extranet.com/customer/customers?customerId[]={customer_id}"
try:
    response = requests.get(customer_metadata_url, headers=headers)
    response.raise_for_status()
    metadata = response.json()
    #print(metadata)
    
    metering_point_id = None
    if 'data' in metadata and metadata['data']:
        contracts = metadata['data'][0].get('contracts', [])
        if contracts:
            metering_point = contracts[0].get('meteringPoint', {})
            metering_point_id = metering_point.get('meteringPointId')
            if metering_point_id:
                print(f"Metering Point ID retrieved: {metering_point_id}")
            else:
                print("No meteringPointId found in the first contract")
        else:
            print("No contracts found in metadata response")
    else:
        print("No data found in metadata response")

except requests.exceptions.RequestException as e:
    print(f"Error fetching customer account metadata: {e}")
    sys.exit(1)

# ... existing code ...

# metering point id
metering_point_id = metering_point_id
# API URL
url = f"https://api.asiakas.aina-extranet.com/consumption/consumption/energy/{metering_point_id}"

params = {
    "customerId": customer_id,
    "end": "2025-01-01T00:00:00+02:00",
    "resolution": "month",
    "netted": "true",
    "start": "2024-01-01T00:00:00+02:00"
}



# Set up the headers
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": user_agent,
    "X-Amz-Date": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
    "X-Api-Key": "",  # If you have an API key, add it here
}

try:
    # Make the GET request
    response = requests.get(url, params=params, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        print("Successfully fetched consumption data")
        
        # Save the data to a file
        with open("consumption_data.json", "w") as outfile:
            json.dump(data, outfile, indent=2)
        print("Saved consumption data to consumption_data.json")
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        # Additional error handling for common API Gateway response codes
        if response.status_code == 403:
            print("Access denied. Please check your authorization token.")
        elif response.status_code == 429:
            print("Too many requests. You might have exceeded the rate limit.")
        elif response.status_code >= 500:
            print("Server error. Please try again later.")

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")

driver.quit()
