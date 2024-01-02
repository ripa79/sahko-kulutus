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

        # Extract the year from the filename
        year = filename.split('-')[0]

        # Extract the table name from the filename
        table_name = filename.split('.')[0]

        # Read CSV into DataFrame
        df = pd.read_csv(filepath)

        # Delete existing data from the source table
        delete_query = sql.SQL("DELETE FROM {}").format(sql.Identifier(table_name))
        cur.execute(delete_query)

        # Commit the deletion
        conn.commit()

        # Insert DataFrame into PostgreSQL table
        for index, row in df.iterrows():
            insert_query = sql.SQL(
                "INSERT INTO {} ({}) VALUES ({})"
            ).format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(map(sql.Identifier, df.columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(df.columns))
            )
            cur.execute(insert_query, tuple(row))

        # Commit the transaction
        conn.commit()

        # Move the processed file to the destination folder
        shutil.move(filepath, os.path.join(DEST_DIR, filename))

# Close the cursor and connection
cur.close()
conn.close()
