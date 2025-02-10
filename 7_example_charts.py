import logging
from pyhive import hive
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_data_from_hive(days=30):
    """Fetch recent data from Hive"""
    try:
        conn = hive.Connection(host='ristoserver', port=10000, database='electricity')
        query = f"""
        SELECT *
        FROM consumption
        WHERE ts_time >= date_sub(current_timestamp(), {days})
        ORDER BY ts_time
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        raise

def plot_daily_consumption(df):
    """Create daily consumption chart"""
    plt.figure(figsize=(12, 6))
    daily_consumption = df.groupby(pd.to_datetime(df['ts_time']).dt.date)['consumption_kwh'].sum()
    
    plt.plot(daily_consumption.index, daily_consumption.values, marker='o')
    plt.title('Daily Electricity Consumption')
    plt.xlabel('Date')
    plt.ylabel('Consumption (kWh)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('charts/daily_consumption.png')
    plt.close()

def plot_hourly_patterns(df):
    """Create hourly consumption patterns chart"""
    plt.figure(figsize=(12, 6))
    df['hour'] = pd.to_datetime(df['ts_time']).dt.hour
    hourly_avg = df.groupby('hour')['consumption_kwh'].mean()
    
    plt.plot(hourly_avg.index, hourly_avg.values, marker='o')
    plt.title('Average Hourly Consumption Pattern')
    plt.xlabel('Hour of Day')
    plt.ylabel('Average Consumption (kWh)')
    plt.grid(True)
    plt.xticks(range(0, 24))
    plt.tight_layout()
    plt.savefig('charts/hourly_pattern.png')
    plt.close()

def plot_price_vs_consumption(df):
    """Create price vs consumption scatter plot"""
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='price_cents_per_kwh', y='consumption_kwh', alpha=0.5)
    plt.title('Price vs Consumption')
    plt.xlabel('Price (cents/kWh)')
    plt.ylabel('Consumption (kWh)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('charts/price_vs_consumption.png')
    plt.close()

def create_heatmap(df):
    """Create weekly consumption heatmap"""
    df['weekday'] = pd.to_datetime(df['ts_time']).dt.day_name()
    df['hour'] = pd.to_datetime(df['ts_time']).dt.hour
    
    pivot_table = df.pivot_table(
        values='consumption_kwh',
        index='weekday',
        columns='hour',
        aggfunc='mean'
    )
    
    # Reorder days
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot_table = pivot_table.reindex(days_order)
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot_table, cmap='YlOrRd', robust=True)
    plt.title('Weekly Consumption Pattern')
    plt.xlabel('Hour of Day')
    plt.ylabel('Day of Week')
    plt.tight_layout()
    plt.savefig('charts/weekly_heatmap.png')
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate electricity consumption charts')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data to analyze')
    parser.add_argument('--all', action='store_true', help='Generate all charts')
    parser.add_argument('--daily', action='store_true', help='Generate daily consumption chart')
    parser.add_argument('--hourly', action='store_true', help='Generate hourly pattern chart')
    parser.add_argument('--price', action='store_true', help='Generate price vs consumption chart')
    parser.add_argument('--heatmap', action='store_true', help='Generate weekly heatmap')
    args = parser.parse_args()

    try:
        # Create charts directory if it doesn't exist
        import os
        os.makedirs('charts', exist_ok=True)

        # Fetch data
        logging.info(f"Fetching last {args.days} days of data")
        df = get_data_from_hive(args.days)

        # Generate requested charts
        if args.all or args.daily:
            logging.info("Generating daily consumption chart")
            plot_daily_consumption(df)

        if args.all or args.hourly:
            logging.info("Generating hourly pattern chart")
            plot_hourly_patterns(df)

        if args.all or args.price:
            logging.info("Generating price vs consumption chart")
            plot_price_vs_consumption(df)

        if args.all or args.heatmap:
            logging.info("Generating weekly heatmap")
            create_heatmap(df)

        if not any([args.all, args.daily, args.hourly, args.price, args.heatmap]):
            parser.print_help()

    except Exception as e:
        logging.error(f"Error generating charts: {str(e)}", exc_info=True)
        raise
