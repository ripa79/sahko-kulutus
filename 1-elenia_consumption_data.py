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

# Wait for the authentication process to complete
#driver.implicitly_wait(10)  # Adjust the wait time as needed
time.sleep(5)
ainalab_button = driver.find_element(By.XPATH, '//button[@aria-label="Elenia Aina"]')
#ainalab_button = driver.find_element(By.XPATH, '//*[contains(text(), "Elenia Aina")]')
#press the button
ainalab_button.click()

time.sleep(2)
# Once logged in, you can navigate to other pages or perform actions
# For example, accessing a protected resource
#protected_resource_url = 'https://asiakas.elenia.fi/kirjaudu'
#driver.get(protected_resource_url)
#time.sleep(10)
# open protected resource https://asiakas.elenia.fi/kulutus
protected_resource_url = 'https://asiakas.elenia.fi/kulutus'
driver.get(protected_resource_url)
time.sleep(5)
print("Opened kulutus")
#print page title
print(driver.title)

# press tab 19 times
for _ in range(10):
    actions.send_keys(Keys.TAB).perform()
    time.sleep(random.uniform(0.1, 0.3))

# show the element and click it
active_element = driver.switch_to.active_element
print(active_element)
# print the text of the element
print(active_element.text)
active_element.click()

time.sleep(30)



# Close the browser
driver.quit()
