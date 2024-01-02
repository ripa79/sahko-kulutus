# Import pandas
import pandas as pd
import locale
import datetime
import xlsxwriter
import os

# Set the locale to en_US.UTF-8
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Get the current year
current_year = datetime.datetime.now().year

# Construct the file paths with the current year
csv_file_path_1 = f"./downloads/{current_year}.csv"
csv_file_path_2 = "./downloads/elenia_hinnat_{current_year}.csv"
csv_output_path = f"./source/{current_year}_netto.csv"
excel_output_path = f"./{current_year}_netto.xlsx"

# Check if the CSV files exist
if not os.path.exists(csv_file_path_1):
    print(f"Error: CSV file {csv_file_path_1} not found.")
    exit()

if not os.path.exists(csv_file_path_2):
    print(f"Error: CSV file {csv_file_path_2} not found.")
    exit()

# Read the csv files with semicolon as delimiter
df1 = pd.read_csv(csv_file_path_1, sep=";")
df1.rename(columns={"Aika": "timeStamp"}, inplace=True)
df2 = pd.read_csv(csv_file_path_2, sep=";")

# Convert the "value" column in df2 from comma-separated numbers to dot-separated numbers and change its title
df2["Electricity price c/kwh"] = df2["value"].str.replace(',', '.').astype(float)
df2["value"] = df2["value"].str.replace(',', '.').astype(float)

# Merge the two dataframes by the timeStamp column
df3 = pd.merge(df1, df2, on="timeStamp", how="inner")

# Read the csv file with semicolon as delimiter
df = df3

# Drop the column (Vuorokauden keskilämpötila)
df.drop("Vuorokauden keskilämpötila", axis=1, inplace=True)

# Create a new column (Netto kulutus Wh) with the calculated data
df["Netto kulutus Wh"] = ((df["Kulutus Wh"] - df["Tuotanto Wh"]) / 1000)

# Define a custom function to calculate production and consumption
def calculate(row):
    netto = (row["Netto kulutus Wh"])
    price = row["Electricity price c/kwh"]
    production = 0
    consumption = 0
    production_cent = 0
    consumption_cent = 0
    if netto < 0:
        production = -netto
        production_cent = production * price
    elif netto > 0:
        consumption = netto
        consumption_cent = consumption * price
    production_cent = production_cent / 100
    dt_string = row["timeStamp"]
    dt_object = datetime.datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S")
    month = dt_object.month
    return pd.Series([production, consumption, consumption_cent, production_cent, month])

# Apply the custom function to each row of the dataframe and create two new columns
df[["production", "consumption", "consumption_cent", "total_price", "month"]] = df.apply(calculate, axis=1)

# Save the modified dataframe to a new csv file
df.to_csv(csv_output_path, index=False)

# Save the dataframe to an Excel file with the desired name and freeze the top row
excel_writer = pd.ExcelWriter(excel_output_path, engine='xlsxwriter')
df3.to_excel(excel_writer, index=False, sheet_name='Sheet1', header=True)

# Get the xlsxwriter workbook and worksheet objects
workbook = excel_writer.book
worksheet = excel_writer.sheets['Sheet1']

# Freeze the top row (row 1) in the worksheet
worksheet.freeze_panes(1, 0)

# Save the Excel file
excel_writer.close()
