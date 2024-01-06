# Import pandas
import pandas as pd
import locale
# Import the datetime module
import datetime
import xlsxwriter
# Set the locale to en_US.UTF-8
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Read the csv files with semicolon as delimiter
df1 = pd.read_csv("./downloads/2024.csv", sep=";")
df1.rename(columns={"Aika": "timeStamp"}, inplace=True)
df2 = pd.read_csv("./downloads/elenia_hinnat.csv", sep=";")

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
    # Get the value of Netto kulutus Wh and convert to kWh
    netto = (row["Netto kulutus Wh"])
   
    price = row["Electricity price c/kwh"]
    # Initialize production and consumption as 0
    production = 0
    consumption = 0
    production_cent = 0
    consumption_cent = 0
    # If netto is negative, production is positive amount of netto
    if netto < 0:
        production = -netto
        production_cent = production * price
    # If netto is positive, consumption is amount of netto
    elif netto > 0:
        consumption = netto
        consumption_cent = consumption * price
    # Return a series with production and consumption
    production_cent = production_cent / 100

    # Define the datetime string
    dt_string = row["timeStamp"]

    # Parse the string into a datetime object using the format YYYY-MM-DDTHH:MN:SE
    dt_object = datetime.datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S")

    # Get the month number from the datetime object
    month = dt_object.month

    return pd.Series([production, consumption, consumption_cent, production_cent, month])

# Apply the custom function to each row of the dataframe and create two new columns
df[["production", "consumption","consumption_cent", "total_price", "month"]] = df.apply(calculate, axis=1)

# Save the modified dataframe to a new csv file
#df.to_csv("./2024_netto.csv", sep=",", index=False)
df.to_csv("./source/2024_netto.csv", index=False)
# Save the dataframe to an Excel file with the desired name and freeze the top row
excel_writer = pd.ExcelWriter("./2024_netto.xlsx", engine='xlsxwriter')
df3.to_excel(excel_writer, index=False, sheet_name='Sheet1', header=True)

# Get the xlsxwriter workbook and worksheet objects
workbook  = excel_writer.book
worksheet = excel_writer.sheets['Sheet1']

# Freeze the top row (row 1) in the worksheet
worksheet.freeze_panes(1, 0)

# Save the Excel file
excel_writer.close()

