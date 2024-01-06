import os
import shutil
import pandas as pd
import psycopg2
from psycopg2 import sql

# Configuration
SOURCE_DIR = "source"
DEST_DIR = "processed"
DB_CONFIG = {
    "dbname": "",
    "user": "",
    "password": "",
    "host": "localhost",
    "port": "5432"
}

# Create destination folder if it doesn't exist
if not os.path.exists(DEST_DIR):
    os.makedirs(DEST_DIR)

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Loop through each CSV file in the source folder
for filename in os.listdir(SOURCE_DIR):
    if filename.endswith(".csv"):
        filepath = os.path.join(SOURCE_DIR, filename)

        # Read CSV into DataFrame
        df = pd.read_csv(filepath)

        # Delete existing data from the source table
        delete_query = sql.SQL("DELETE FROM \"2024_netto\"")
        cur.execute(delete_query)

        # Commit the deletion
        conn.commit()

        # Insert DataFrame into PostgreSQL table
        for index, row in df.iterrows():
            insert_query = sql.SQL(
                "INSERT INTO \"2024_netto\" (\"timeStamp\", \"Kulutus Wh\", \"Tuotanto Wh\", \"timeStampDay\", \"timeStampHour\", \"value\", "
                "\"priceArea\", \"unit\", \"Electricity price c/kwh\", \"Netto kulutus Wh\", \"production\", "
                "\"consumption\", \"consumption_cent\", \"total_price\", \"month\""
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            cur.execute(
                insert_query,
                (
                    row['timeStamp'],
                    row['Kulutus Wh'],
                    row['Tuotanto Wh'],
                    row['timeStampDay'],
                    row['timeStampHour'],
                    row['value'],
                    row['priceArea'],
                    row['unit'],
                    row['Electricity price c/kwh'],
                    row['Netto kulutus Wh'],
                    row['production'],
                    row['consumption'],
                    row['consumption_cent'],
                    row['total_price'],
                    row['month']
                )
            )

        # Commit the transaction
        conn.commit()

        # Move the processed file to the destination folder
        shutil.move(filepath, os.path.join(DEST_DIR, filename))

# Close the cursor and connection
cur.close()
conn.close()

