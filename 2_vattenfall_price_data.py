import sys
import json
import csv
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
}

# Get the current year
#current_year = datetime.now().year
current_year = os.getenv('YEAR')
# Generate the start and end dates for the current year
start_date = f"{current_year}-01-01"
end_date = f"{current_year}-12-31"

url = f"https://www.vattenfall.fi/api/price/spot/{start_date}/{end_date}?lang=fi"
print(f"Loading data from {url}...")
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()  # Parse the JSON data from the response
    print("Data has been loaded from the URL")
else:
    print("Error:", response.status_code)
    exit()  # Exit the program if there is an error

# Add VAT (25.5%) to the values
VAT_RATE = 0.255
for row in data:
    row['value'] = round(row['value'] * (1 + VAT_RATE), 2)

# ensure downloads folder exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

csv_filename = f"downloads/vattenfall_hinnat_{current_year}.csv"

# Extract the keys from the first dictionary to use as header
fieldnames = data[0].keys()

# Write data to CSV file using semicolon as the separator
with open(csv_filename, mode='w', newline='') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writeheader()

    for row in data:
        writer.writerow(row)

print(f"Data saved {csv_filename}")
