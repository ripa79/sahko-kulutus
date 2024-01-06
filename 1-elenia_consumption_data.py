from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

downloadDir = f"{os.getcwd()}//downloads//"
# Make sure path exists.
# Path(downloadDir).mkdir(parents=True, exist_ok=True)
# output file will be YYYY.csv (for example 2024.csv)

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
username = ''
password = ''

# Create a new Chrome browser instance
driver = webdriver.Chrome(options=chromeOptions)

# Navigate to the authentication page
driver.get(auth_url)
delay = 3 # seconds
try:
    myElem = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'signin-email')))
    print("Page is ready!")
except TimeoutException:
    print("Loading took too much time!")

# Find the username and password input fields using input IDs
#username_element = driver.find_element_by_xpath("//input[@name='signin-email' and @id='signin-email' and @type='email'")

#username_element = driver.find_element(By.ID, "signin-email")
username_element = driver.find_element(By.XPATH, "//input[@name='signin-email']")
password_element = driver.find_element(By.XPATH, "//input[@name='password']")

time.sleep(5)
# Fill in the username and password fields
username_element.send_keys(username)
password_element.send_keys(password)

# Submit the form
print("Submitting form...")
password_element.send_keys(Keys.ENTER)

# Wait for the authentication process to complete
driver.implicitly_wait(10)  # Adjust the wait time as needed
time.sleep(5)
ainalab_button = driver.find_element(By.XPATH, '//button[@aria-label="AinaLab"]')
#ainalab_button = driver.find_element(By.XPATH, '//*[contains(text(), "AinaLab")]')
ainalab_button.send_keys(Keys.RETURN)

time.sleep(2)
# Once logged in, you can navigate to other pages or perform actions
# For example, accessing a protected resource
protected_resource_url = 'https://ainalab.aws.elenia.fi/?gsrn=643006966022748876&view=energy'
driver.get(protected_resource_url)
time.sleep(2)

tuo_tiedot = driver.find_element(By.XPATH, '//*[contains(text(), "csv")]')
tuo_tiedot.click()
time.sleep(2)
# Extract the page content
page_content = driver.page_source
print(page_content)

# Close the browser
driver.quit()
