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
from urllib.parse import urlencode

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
chromeOptions.add_argument("--headless")
chromeOptions.add_experimental_option("prefs", preferences)

# Website URL
auth_url = 'https://idm.asiakas.elenia.fi/'

# Create a new Chrome browser instance
driver = webdriver.Chrome(options=chromeOptions)

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
    for char in password:
        actions.send_keys(char).perform()
        time.sleep(random.uniform(0.05, 0.2))
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

# get the access token from the cookies it ends accessToken
access_token = None
for cookie in cookies:
    if cookie['name'].endswith('.accessToken'):
        access_token = cookie['value']
        break

# Print the access token
if access_token:
    print("Access Token:", access_token)
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

url = "https://api.asiakas.aina-extranet.com/consumption/consumption/energy/FI_VFV000_2274887"

params = {
    "customerId": "elenia_7191131",
    "end": "2025-01-01T00:00:00+02:00",
    "resolution": "month",
    "netted": "true",
    "start": "2024-01-01T00:00:00+02:00"
}

# Get the User-Agent from the Selenium WebDriver
user_agent = driver.execute_script("return navigator.userAgent;")

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

# Print debug information
print(f"Request URL: {response.request.url}")
print(f"Request headers: {response.request.headers}")
print(f"Response headers: {response.headers}")

# ... (keep the rest of the code, including closing the driver)
