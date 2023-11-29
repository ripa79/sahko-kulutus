import json
import csv

import requests

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
}

url = "https://www.vattenfall.fi/api/price/spot/2023-01-01/2023-12-31?lang=fi"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json() # Parse the JSON data from the response
    print("Data has been loaded from the URL")
else:
    print("Error:", response.status_code)
    exit() # Exit the program if there is an error

csv_filename = "downloads/elenia_hinnat.csv"

# Extract the keys from the first dictionary to use as header
fieldnames = data[0].keys()

# Write data to CSV file using semicolon as the separator and comma as decimal separator
with open(csv_filename, mode='w', newline='') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writeheader()

    for row in data:
        row_with_comma_decimal = {key: str(value).replace('.', ',') if isinstance(value, float) else value for key, value in row.items()}
        writer.writerow(row_with_comma_decimal)

print(f"Data saved {csv_filename}")
