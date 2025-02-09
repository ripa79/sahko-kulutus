from dremio_simple_query.connect import get_token, DremioConnection
import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# Dremio login details
login_endpoint = "http://192.168.11.187:9047/apiv2/login"
payload = {
    "userName": "admin",  # Dremio username
    "password": "Passw0rd"  # Dremio password
}

# Get the token
token = get_token(uri=login_endpoint, payload=payload)

# Dremio Arrow Flight endpoint (no SSL for local setup)
arrow_endpoint = "grpc://192.168.11.187:32010"

# Create the connection
dremio = DremioConnection(token, arrow_endpoint)
#Step 2: Query the Gold Dataset (sales_data_gold)
#Next, we'll query the sales_data_gold dataset from Dremio using the toPolars() method to return the data in a Polars DataFrame.

#python
#Copy code
# Query the Gold dataset
query = "SELECT * FROM nessie.consumption.cumulative_2025;"
df = dremio.toPolars(query)

# Display the Polars DataFrame
print(df)
#Step 3: Visualize the Data with Seaborn
#Using the queried data, we can now visualize key metrics. In this example, we'll plot total sales by product.

#python
#Copy code
# Convert the Polars DataFrame to a Pandas DataFrame for Seaborn visualization

# Convert to Pandas and ensure proper datetime format
df_pandas = df.to_pandas()
df_pandas['date'] = pd.to_datetime(df_pandas['date'])

# Set up the visualization style
sns.set_theme(style="whitegrid")

# Create subplots for different metrics
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 14))

# Plot 1: Daily Consumption and Price
ax1.plot(df_pandas['date'], df_pandas['daily_consumption_kWh'], color='royalblue', label='Daily Consumption')
ax1.set_ylabel('kWh', color='royalblue')
ax1.tick_params(axis='y', labelcolor='royalblue')
ax1.set_title('Daily Energy Consumption & Price')

ax1b = ax1.twinx()
ax1b.plot(df_pandas['date'], df_pandas['avg_price_cents_per_kWh'], color='darkorange', label='Price')
ax1b.set_ylabel('Cents/kWh', color='darkorange')
ax1b.tick_params(axis='y', labelcolor='darkorange')

# Plot 2: Cumulative Metrics with dual y-axes
ax2.plot(df_pandas['date'], df_pandas['cumulative_cost_euros'], color='purple', label='Cost')
ax2.set_title('Cumulative Consumption & Cost')
ax2.set_ylabel('Cost (€)', color='purple')
ax2.tick_params(axis='y', labelcolor='purple')

ax2b = ax2.twinx()
ax2b.plot(df_pandas['date'], df_pandas['cumulative_consumption_kWh'], color='green', label='Consumption')
ax2b.set_ylabel('Consumption (kWh)', color='green')
ax2b.tick_params(axis='y', labelcolor='green')

# Add combined legend
lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2b.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

# Plot 3: Daily Costs
ax3.bar(df_pandas['date'], df_pandas['total_daily_cost_euros'], color='teal', width=1)
ax3.set_title('Daily Energy Costs')
ax3.set_ylabel('€')

# Format x-axis dates
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()