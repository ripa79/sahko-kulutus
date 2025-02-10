import logging
from pyhive import hive
import pandas as pd
import os
from datetime import datetime
import pytz
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def query_hive(query):
    logging.info(f"Executing query: {query}")
    try:
        conn = hive.Connection(host='ristoserver', port=10000, database='nyc')
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Error executing query: {str(e)}")
        raise

def create_database_and_table(conn):
    cursor = conn.cursor()
    try:
        logging.info("Creating database if not exists")
        cursor.execute("CREATE DATABASE IF NOT EXISTS electricity")
        
        logging.info("Switching to electricity database")
        cursor.execute("USE electricity")
        
        logging.info("Creating table if not exists")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumption (
                ts_time TIMESTAMP,
                consumption_kWh DOUBLE,
                price_cents_per_kWh DOUBLE,
                cost_euros DOUBLE
            )
            STORED BY ICEBERG
            TBLPROPERTIES (
                'format-version' = '2',
                'write.format.default' = 'PARQUET',
                'write.parquet.compression-codec' = 'SNAPPY',
                'write.metadata.delete-after-commit.enabled'='true',
                'write.metadata.previous-versions-max'='10',
                'write.target-file-size-bytes'='536870912'
            )
        """)
    except Exception as e:
        logging.error(f"Error in create_database_and_table: {str(e)}")
        raise
    finally:
        logging.info("Closing cursor")
        cursor.close()

def drop_table(conn):
    cursor = conn.cursor()
    try:
        logging.info("Dropping consumption table")
        cursor.execute("USE electricity")
        cursor.execute("DROP TABLE IF EXISTS consumption")
        logging.info("Table dropped successfully")
    except Exception as e:
        logging.error(f"Error dropping table: {str(e)}")
        raise
    finally:
        cursor.close()

def drop_database(conn):
    cursor = conn.cursor()
    try:
        logging.info("Dropping electricity database")
        cursor.execute("DROP DATABASE IF EXISTS electricity CASCADE")
        logging.info("Database dropped successfully")
    except Exception as e:
        logging.error(f"Error dropping database: {str(e)}")
        raise
    finally:
        cursor.close()

def read_local_csv():
    csv_path = "processed/combined_data.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Error: {csv_path} not found")
    return pd.read_csv(csv_path)

def convert_timestamp(ts_str):
    # Parse the ISO format timestamp with timezone
    dt = datetime.fromisoformat(ts_str)
    # Convert to UTC and format for Hive
    utc_dt = dt.astimezone(pytz.UTC)
    return utc_dt.strftime('%Y-%m-%d %H:%M:%S')

def insert_data_to_hive(conn, df):
    cursor = conn.cursor()
    try:
        cursor.execute("USE electricity")
        
        # Create batch insert query
        values_list = []
        for _, row in df.iterrows():
            hive_timestamp = convert_timestamp(row['timestamp'])
            values_list.append(
                f"('{hive_timestamp}', {row['consumption_kWh']}, "
                f"{row['price_cents_per_kWh']}, {row['cost_euros']})"
            )
        
        # Execute batch insert
        batch_size = 1000
        for i in range(0, len(values_list), batch_size):
            batch = values_list[i:i + batch_size]
            insert_query = f"""
            INSERT INTO consumption
            VALUES {','.join(batch)}
            """
            logging.debug(f"Executing batch insert with {len(batch)} rows")
            cursor.execute(insert_query)
            
    except Exception as e:
        logging.error(f"Error in insert_data_to_hive: {str(e)}")
        raise
    finally:
        cursor.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage electricity consumption data in Hive/Iceberg')
    parser.add_argument('--drop-table', action='store_true', help='Drop the consumption table')
    parser.add_argument('--drop-database', action='store_true', help='Drop the electricity database')
    parser.add_argument('--upload', action='store_true', help='Upload data from CSV to Hive')
    args = parser.parse_args()

    try:
        conn = hive.Connection(host='ristoserver', port=10000)

        if args.drop_table:
            drop_table(conn)
        if args.drop_database:
            drop_database(conn)
        if args.upload:
            # Read local CSV
            logging.info("Reading local CSV file")
            data_df = read_local_csv()
            
            # Create database and table structure
            logging.info("Setting up database and table")
            create_database_and_table(conn)
            
            # Insert data
            logging.info("Starting data insertion")
            insert_data_to_hive(conn, data_df)
            logging.info("Successfully inserted data into Hive table")
        
        if not any([args.drop_table, args.drop_database, args.upload]):
            parser.print_help()

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        raise
    finally:
        conn.close()
        logging.info("Connection closed")
