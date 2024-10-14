import json
import csv
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# constants
vattenfall_price_data_file = 'downloads/vattenfall_hinnat_2024.csv'
elenia_consumption_data_file = 'downloads/consumption_data.json'
combined_data_file = 'processed/combined_data.csv'
SPOT_MARGIN = float(os.getenv('SPOT_MARGIN'))

# Load Elenia consumption data
with open(elenia_consumption_data_file, 'r') as f:
    consumption_data = json.load(f)

# Load Vattenfall price data
price_data = {}
with open(vattenfall_price_data_file, 'r') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        timestamp = datetime.strptime(row['timeStamp'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=ZoneInfo("Europe/Helsinki"))
        price_data[timestamp] = float(row['value'])

# Combine data
combined_data = []
for entry in consumption_data['data']['productSeries'][0]['data']:
    timestamp_utc = datetime.strptime(entry['startTime'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=ZoneInfo("UTC"))
    timestamp_helsinki = timestamp_utc.astimezone(ZoneInfo("Europe/Helsinki"))
    consumption = entry['value']
    
    # Find the corresponding price
    price_timestamp = timestamp_helsinki.replace(minute=0, second=0, microsecond=0)
    price = price_data.get(price_timestamp)
    
    if price is not None:
        cost = consumption * (price + SPOT_MARGIN) / 100  # Convert cents to euros
        combined_data.append({
            'timestamp': timestamp_helsinki.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'consumption_kWh': consumption,
            'price_cents_per_kWh': price,
            'cost_euros': cost
        })

# Sort the combined data by timestamp
combined_data.sort(key=lambda x: x['timestamp'])

# ensure processed folder exists
if not os.path.exists("processed"):
    os.makedirs("processed")

# Write the combined data to a CSV file
with open(combined_data_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['timestamp', 'consumption_kWh', 'price_cents_per_kWh', 'cost_euros'])
    writer.writeheader()
    writer.writerows(combined_data)

print(f"Combined data has been written to {combined_data_file}")
