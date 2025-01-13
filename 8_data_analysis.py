import logging
from pyhive import hive
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_consumption_data():
    conn = hive.Connection(host='ristoserver', port=10000, database='electricity')
    return pd.read_sql("SELECT * FROM consumption", conn)

def print_ascii_banner():
    print("""
    ⚡️ Electricity Consumption Analysis ⚡️
    =====================================
    """)

def create_ascii_histogram(data, bins=10, width=50):
    hist, bins = np.histogram(data, bins=bins)
    max_height = max(hist)
    for count in hist:
        bar = '█' * int(count/max_height * width)
        print(f"{bar:50} | {count:3d}")

def create_ascii_trend(data, width=50):
    values = data.fillna(0).rolling(24).mean()  # Handle NaN values
    min_val, max_val = values.min(), values.max()
    
    # Handle case where all values are the same
    if max_val == min_val:
        pos = width // 2
        for _ in values:
            print(' ' * pos + '•' + ' ' * (width - pos - 1))
    else:
        for val in values:
            if pd.isna(val):
                continue
            normalized = (val - min_val) / (max_val - min_val)
            normalized = np.clip(normalized, 0, 1)
            pos = int(normalized * width)
            line = ' ' * pos + '•' + ' ' * (width - pos - 1)
            print(line)

def main():
    print_ascii_banner()
    df = get_consumption_data()
    
    print("\n📊 Consumption Distribution (kWh)")
    print("================================")
    create_ascii_histogram(df['consumption.consumption_kwh'])
    
    print("\n📈 24h Moving Average Trend")
    print("=========================")
    create_ascii_trend(df['consumption.consumption_kwh'])
    
    print("\n📉 Statistics Summary")
    print("==================")
    print(f"""
    Total Cost: {'€':>3} {df['consumption.cost_euros'].sum():.2f}
    Max Usage:  {'⚡️':>3} {df['consumption.consumption_kwh'].max():.2f} kWh
    Avg Price:  {'¢':>3} {df['consumption.price_cents_per_kwh'].mean():.2f}/kWh
    """)

if __name__ == "__main__":
    main()
