import csv
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import requests
import pytz
import os
from dotenv import load_dotenv
from dateutil.parser import isoparse

# Load environment variables
load_dotenv()

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'

def read_combined_data(filename='combined_data.csv'):
    filepath = os.path.join('processed', filename)
    data = []
    with open(filepath, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            timestamp = isoparse(row['timestamp'])
            data.append({
                'date': timestamp.date(),
                'hour': timestamp.hour,
                'consumption': float(row['consumption_kWh']),
                'price': float(row['price_cents_per_kWh']),
                'cost': float(row['cost_euros'])
            })
    return data

def analyze_data(data):
    total_consumption = sum(row['consumption'] for row in data)
    total_cost = sum(row['cost'] for row in data)
    average_price = sum(row['price'] for row in data) / len(data)

    monthly_data = defaultdict(lambda: {'consumption': 0, 'cost': 0, 'hours': 0, 'daily_consumption': defaultdict(float), 'prices': []})
    for row in data:
        month = row['date'].strftime('%Y-%m')
        monthly_data[month]['consumption'] += row['consumption']
        monthly_data[month]['cost'] += row['cost']
        monthly_data[month]['hours'] += 1
        monthly_data[month]['prices'].append(row['price'])
        monthly_data[month]['daily_consumption'][row['date'].strftime('%Y-%m-%d')] += row['consumption']

    # Calculate monthly averages
    for month, data in monthly_data.items():
        num_days = len(data['daily_consumption'])
        data['average_daily_consumption'] = data['consumption'] / num_days if num_days > 0 else 0
        data['average_monthly_price'] = sum(data['prices']) / len(data['prices']) if data['prices'] else 0

    fixed_price = float(os.getenv('FIXED_PRICE', 8.5))  # Default to 8.5 if not set
    fixed_price_total_cost = total_consumption * fixed_price / 100  # Convert to EUR

    for month, data in monthly_data.items():
        data['fixed_price_cost'] = data['consumption'] * fixed_price / 100


    savings = fixed_price_total_cost - total_cost

    return {
        'total_consumption': total_consumption,
        'total_cost': total_cost,
        'average_price': average_price,
        'monthly_data': monthly_data,
        'fixed_price_total_cost': fixed_price_total_cost,
        'savings': savings,
        'fixed_price': fixed_price
    }

def get_current_spot_price():
    url = "https://api.porssisahko.net/v1/latest-prices.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        now = datetime.now(pytz.timezone('Europe/Helsinki'))
        for price in data['prices']:
            # Remove the 'Z' and parse the string
            start_time = datetime.fromisoformat(price['startDate'].rstrip('Z')).replace(tzinfo=pytz.UTC)
            end_time = datetime.fromisoformat(price['endDate'].rstrip('Z')).replace(tzinfo=pytz.UTC)
            # Convert to Helsinki time
            start_time = start_time.astimezone(pytz.timezone('Europe/Helsinki'))
            end_time = end_time.astimezone(pytz.timezone('Europe/Helsinki'))
            if start_time <= now < end_time:
                return price['price']
    return None

def print_current_spot_price(price):
    if price is not None:
        print(f"\n{Colors.PURPLE}Current Spot Price: {Colors.YELLOW}{price:.2f} snt/kWh{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}Unable to fetch current spot price.{Colors.RESET}")

def print_analysis(analysis):
    # Get the current time in Finland's timezone (EEST/EET)
    finland_tz = pytz.timezone('Europe/Helsinki')
    current_time = datetime.now(finland_tz)

    # Determine if it's EEST (UTC+3) or EET (UTC+2)
    if current_time.tzinfo.dst(current_time) != timedelta(0):
        tz_name = "EEST"
    else:
        tz_name = "EET"

    current_time_str = current_time.strftime(f'%Y-%m-%d %H:%M:%S {tz_name}')

    print(f"\n{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.YELLOW}Electricity Price and Consumption Analysis{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.PURPLE}Analysis generated on: {Colors.YELLOW}{current_time_str}{Colors.RESET}")

    # Fetch and print current spot price
    current_price = get_current_spot_price()
    print_current_spot_price(current_price)

    print(f"\n{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.YELLOW}Annual Summary{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 80}{Colors.RESET}")

    # Add total year consumption with average price calculation
    total_year_cost_avg = analysis['total_consumption'] * analysis['average_price'] / 100
    print(f"{Colors.CYAN}Total year cost with average price ({analysis['average_price']:.2f} snt/kWh): {Colors.YELLOW}{total_year_cost_avg:.2f} EUR{Colors.RESET}")

    average_year_price = analysis['total_cost'] / (analysis['total_consumption'] / 100)
    print(f"{Colors.CYAN}Average Year Actual Price: {Colors.YELLOW}{average_year_price:.2f} snt/kWh{Colors.RESET}")
    print(f"{Colors.CYAN}Spot price average for the whole year: {Colors.YELLOW}{analysis['average_price']:.2f} snt/kWh{Colors.RESET}")
    print(f"\n{Colors.PURPLE}Monthly analysis:{Colors.RESET}")
    fixed_price = analysis['fixed_price']  # Use the fixed price from the analysis results

    # Define column widths
    month_width = 10
    price_width = 15
    consumption_width = 25
    cost_width = 20
    avg_cost_width = 25

    # Print header
    print(f"\n{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.YELLOW}Monthly Breakdown{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{'Month':<{month_width}} {'Avg Spot':<{price_width}} {'Consumption':<{consumption_width}} {'Actual Cost':<{cost_width}} {'Cost with Avg Price':<{avg_cost_width}}")

    for month, data in analysis['monthly_data'].items():
        avg_price = data['average_monthly_price']
        if avg_price < fixed_price:
            arrow = f"{Colors.GREEN}▼{Colors.RESET}"
        else:
            arrow = f"{Colors.RED}▲{Colors.RESET}"

        # Calculate cost with average price for this month
        cost_with_avg_price = data['consumption'] * analysis['average_price'] / 100

        month_str = f"{Colors.BLUE}{month}:{Colors.RESET}"
        price_str = f"{arrow} {Colors.YELLOW}{avg_price:.2f} snt/kWh{Colors.RESET}"
        consumption_str = f"Consumption: {Colors.YELLOW}{data['consumption']:.2f} kWh{Colors.RESET}"
        cost_str = f"Cost: {Colors.YELLOW}{data['cost']:.2f} EUR{Colors.RESET}"
        avg_cost_str = f"{Colors.YELLOW}{cost_with_avg_price:.2f} EUR{Colors.RESET}"

        print(f"{month_str:<{month_width}} {price_str:<{price_width}} {consumption_str:<{consumption_width}} {cost_str:<{cost_width}} {avg_cost_str:<{avg_cost_width}}")

    print(f"\n{Colors.CYAN}Total consumption: {Colors.YELLOW}{analysis['total_consumption']:.2f} kWh{Colors.RESET}")
    print(f"{Colors.CYAN}Total cost with spot pricing: {Colors.YELLOW}{analysis['total_cost']:.2f} EUR{Colors.RESET}")
    print(f"{Colors.CYAN}Total cost with {analysis['fixed_price']} snt/kWh fixed price: {Colors.YELLOW}{analysis['fixed_price_total_cost']:.2f} EUR{Colors.RESET}")

    print(f"\n{Colors.YELLOW}Final Analysis{Colors.RESET}")

    if analysis['savings'] > 0:
        print(f"{Colors.WHITE}With the spot price contract, you saved:{Colors.RESET}")
        print(f"{Colors.GREEN}{analysis['savings']:.2f} EUR over the year.{Colors.RESET}")
        print(f"{Colors.GRAY}Compared to the fixed-price contract ({analysis['fixed_price']} snt/kWh), you spent less.{Colors.RESET}")
    else:
        print(f"{Colors.WHITE}With the spot price contract, you spent more:{Colors.RESET}")
        print(f"{Colors.RED}{-analysis['savings']:.2f} EUR over the year.{Colors.RESET}")
        print(f"{Colors.GRAY}The fixed-price contract ({analysis['fixed_price']} snt/kWh) would have been cheaper.{Colors.RESET}")

    percent_diff = (analysis['savings'] / analysis['fixed_price_total_cost']) * 100
    if percent_diff > 0:
        print(f"{Colors.WHITE}This is equivalent to a {Colors.GREEN}{abs(percent_diff):.2f}% decrease{Colors.WHITE} in your total electricity cost.{Colors.RESET}")
    else:
        print(f"{Colors.WHITE}This is equivalent to a {Colors.RED}{abs(percent_diff)::.2f}% increase{Colors.WHITE} in your total electricity cost.{Colors.RESET}")

    # Update the conclusion line
    print(f"\n{Colors.YELLOW}Conclusion: {Colors.WHITE}The {'spot' if analysis['savings'] > 0 else 'fixed'} price contract was more beneficial for you this year.{Colors.RESET}")

def plot_monthly_analysis(analysis):
    fixed_price = analysis['fixed_price']
    monthly_summary = []

    for month, data in analysis['monthly_data'].items():
        fixed_cost = data['consumption'] * fixed_price / 100  # Convert to EUR
        savings = fixed_cost - data['cost']
        monthly_summary.append({
            'Month': month,
            'savings': savings,
            'total_cost': data['cost'],
            'fixed_cost': fixed_cost,
            'average_daily_consumption': data['average_daily_consumption'], # Add average daily consumption
            'average_monthly_price' : data['average_monthly_price'],       #Add average montly price
        })

    # Sort the monthly summary by date
    monthly_summary.sort(key=lambda x: datetime.strptime(x['Month'], '%Y-%m'))

    # Create a figure with three subplots: savings, cost comparison, and average daily consumption
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 8))

    # Plotting the monthly savings
    bars = ax1.bar([item['Month'] for item in monthly_summary], [item['savings'] for item in monthly_summary], color='skyblue')
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Savings (EUR)')
    ax1.set_title(f'Monthly Savings: Spot Price vs Fixed {fixed_price} snt/kWh Contract')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.2f}', ha='center', va='bottom')

    # Plotting comparison between spot price costs and fixed price costs per month
    ax2.plot([item['Month'] for item in monthly_summary], [item['total_cost'] for item in monthly_summary], label='Spot Price Cost', marker='o', color='b')
    ax2.plot([item['Month'] for item in monthly_summary], [item['fixed_cost'] for item in monthly_summary], label=f'Fixed Price Cost ({fixed_price} snt/kWh)', marker='o', color='r')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('Total Cost (EUR)')
    ax2.set_title('Monthly Cost Comparison: Spot vs Fixed Price')
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend()
    ax2.grid(axis='y', linestyle='--', alpha=0.7)

    # Plotting average daily consumption
    ax3.plot([item['Month'] for item in monthly_summary], [item['average_daily_consumption'] for item in monthly_summary], label='Avg Daily Consumption', marker='o', color='g')
    ax3.set_xlabel('Month')
    ax3.set_ylabel('Average Daily Consumption (kWh)')
    ax3.set_title('Monthly Average Daily Consumption')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(axis='y', linestyle='--', alpha=0.7)

    # Adjust layout and display the plot
    plt.tight_layout()
    plt.show()


# Main execution
if __name__ == "__main__":
    data = read_combined_data()
    analysis = analyze_data(data)
    print_analysis(analysis)
    plot_monthly_analysis(analysis)