import json
import csv
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# constants
SPOT_MARGIN = float(os.getenv('SPOT_MARGIN'))
YEAR = os.getenv('YEAR')
vattenfall_price_data_file = f'downloads/vattenfall_hinnat_{YEAR}.csv'
elenia_consumption_data_file = 'downloads/consumption_data.json'
combined_data_file = 'processed/combined_data.csv'

# Load Elenia consumption data
with open(elenia_consumption_data_file, 'r') as f:
    consumption_raw = json.load(f)

# Create dictionary for consumption data
consumption_dict = {}

# Process consumption data - use regular hourly values instead of netted
for month in consumption_raw['months']:
    if 'hourly_values' in month and month['hourly_values']:  # Check if hourly_values exists and is not empty
        for hourly in month['hourly_values']:
            # Handle both cases: with 't' key and without
            if 't' in hourly:
                timestamp_str = hourly['t']
            else:
                # If no timestamp, construct it from the month data
                # Assuming the values are in order starting from the beginning of the month
                month_num = month['month']
                hour_index = month['hourly_values'].index(hourly)
                timestamp = datetime(int(YEAR), month_num, 1) + timedelta(hours=hour_index)
                timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S')
            
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=ZoneInfo("Europe/Helsinki"))
            consumption_dict[timestamp] = hourly['v'] / 1000  # Convert to kWh

# Load Vattenfall price data
price_data = {}
with open(vattenfall_price_data_file, 'r') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        timestamp = datetime.strptime(row['timeStamp'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=ZoneInfo("Europe/Helsinki"))
        price_data[timestamp] = float(row['value'])

# Add debug information
print("\nDebug Information:")
print("=================")
print(f"\nNetted Consumption Data ({len(consumption_dict)} records):")
print(f"First record: {min(consumption_dict.keys())}")
print(f"Last record: {max(consumption_dict.keys())}")

print(f"\nPrice Data ({len(price_data)} records):")
print(f"First record: {min(price_data.keys())}")
print(f"Last record: {max(price_data.keys())}")

# Add more detailed debug information
print("\nDetailed Debug Information:")
print("=================")
print(f"\nNetted Consumption Data Details:")
print("Last 5 records:")
last_keys = sorted(consumption_dict.keys())[-5:]
for key in last_keys:
    print(f"{key}: {consumption_dict[key]}")

# Combine data
combined_data = []
for timestamp in consumption_dict:
    net_consumption = consumption_dict[timestamp]
    price = price_data.get(timestamp)
    
    if price is not None:
        cost = net_consumption * (price + SPOT_MARGIN) / 100  # Convert cents to euros
        combined_data.append({
            'timestamp': timestamp.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'consumption_kWh': net_consumption,
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
    writer = csv.DictWriter(f, fieldnames=['timestamp', 'consumption_kWh', 
                                         'price_cents_per_kWh', 'cost_euros'])
    writer.writeheader()
    writer.writerows(combined_data)

print(f"Combined data has been written to {combined_data_file}")
