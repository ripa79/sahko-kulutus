import os
from dotenv import load_dotenv
import shutil
import pandas as pd
import psycopg2
from psycopg2 import sql
import argparse
import logging
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_operations.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Configuration
SOURCE_DIR = "processed"
DEST_DIR = "moved_to_db"
DB_CONFIG = {
    "dbname": os.getenv('DATABASE'),
    "user": os.getenv('DATABASE_USER'),
    "password": os.getenv('DATABASE_PASSWORD'),
    "host": os.getenv('DATABASE_HOST'),
    "port": "5432"
}

def delete_database():
    postgres_config = DB_CONFIG.copy()
    postgres_config['dbname'] = 'postgres'
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(**postgres_config)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists before attempting to delete
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (os.getenv('DATABASE'),))
        exists = cur.fetchone()
        
        if exists:
            # Terminate all connections to the database
            cur.execute(sql.SQL("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
            """), [os.getenv('DATABASE')])
            
            # Drop the database
            cur.execute(sql.SQL("DROP DATABASE {}").format(
                sql.Identifier(os.getenv('DATABASE'))
            ))
            logging.info(f"Database {os.getenv('DATABASE')} has been deleted")
        else:
            logging.info(f"Database {os.getenv('DATABASE')} does not exist")
        
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Error deleting database: {e}", exc_info=True)
        raise

def init_database():
    postgres_config = DB_CONFIG.copy()
    postgres_config['dbname'] = 'postgres'
    
    try:
        # Connect to default postgres database first
        conn = psycopg2.connect(**postgres_config)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create database if it doesn't exist
        try:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(os.getenv('DATABASE'))
            ))
        except psycopg2.errors.DuplicateDatabase:
            logging.info(f"Database {os.getenv('DATABASE')} already exists")
        
        cur.close()
        conn.close()

        # Now connect to our database and create table
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Updated table creation with primary key
        create_table_query = """
        CREATE TABLE IF NOT EXISTS consumption_data (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            consumption_kWh DOUBLE PRECISION NOT NULL,
            price_cents_per_kWh DOUBLE PRECISION NOT NULL,
            cost_euros DOUBLE PRECISION NOT NULL,
            UNIQUE (timestamp)
        );
        """
        cur.execute(create_table_query)
        conn.commit()
        
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Database initialization error: {e}", exc_info=True)
        raise

def drop_table():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("DROP TABLE IF EXISTS consumption_data")
        conn.commit()
        logging.info("Table 'consumption_data' has been dropped")
        
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Error dropping table: {e}", exc_info=True)
        raise

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process consumption data and manage database.')
    parser.add_argument('--delete-db', action='store_true', help='Delete the database and exit')
    parser.add_argument('--drop-table', action='store_true', help='Drop the consumption_data table and exit')
    args = parser.parse_args()

    if args.delete_db:
        delete_database()
        return

    if args.drop_table:
        drop_table()
        return

    # Initialize database and process files
    init_database()
    
    # Create destination folder if it doesn't exist
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Loop through each CSV file in the source folder
        for filename in os.listdir(SOURCE_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(SOURCE_DIR, filename)
                
                try:
                    # Read CSV into DataFrame
                    df = pd.read_csv(filepath)
                    
                    # Log DataFrame info before conversion
                    logging.debug(f"DataFrame dtypes before conversion:\n{df.dtypes}")
                    
                    # Convert numerical columns to float
                    df['consumption_kWh'] = df['consumption_kWh'].astype(float)
                    df['price_cents_per_kWh'] = df['price_cents_per_kWh'].astype(float)
                    df['cost_euros'] = df['cost_euros'].astype(float)
                    
                    # Convert timestamp column to datetime with UTC
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                    
                    # Log DataFrame info after conversion
                    logging.debug(f"DataFrame dtypes after conversion:\n{df.dtypes}")
                    
                    # Sample data check
                    logging.debug(f"First row data:\n{df.iloc[0]}")
                    logging.debug(f"Data types of first row:\n{df.iloc[0].apply(type)}")
                    
                    year = df['timestamp'].dt.year.iloc[0]
                    
                    # Delete existing data for the year before inserting new data
                    #cur.execute(
                    #    "DELETE FROM consumption_data WHERE EXTRACT(YEAR FROM timestamp) = %s",
                    #    (year,)
                    #)
                    logging.info(f"Deleted existing data for year {year}")

                    # Convert DataFrame to list of tuples with Python native types
                    data_tuples = [(
                        row['timestamp'].to_pydatetime(),
                        float(row['consumption_kWh']),
                        float(row['price_cents_per_kWh']),
                        float(row['cost_euros'])
                    ) for _, row in df.iterrows()]

                    # Modified insert query (specify columns explicitly)
                    insert_query = """
                        INSERT INTO consumption_data 
                        (timestamp, consumption_kWh, price_cents_per_kWh, cost_euros)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (timestamp) DO UPDATE SET
                            consumption_kWh = EXCLUDED.consumption_kWh,
                            price_cents_per_kWh = EXCLUDED.price_cents_per_kWh,
                            cost_euros = EXCLUDED.cost_euros
                    """
                    
                    cur.executemany(insert_query, data_tuples)

                    # Commit the transaction
                    conn.commit()

                    # Move the processed file
                    shutil.move(filepath, os.path.join(DEST_DIR, filename))
                    logging.info(f"Successfully processed {filename}")

                except (ValueError, AttributeError) as e:
                    logging.error(f"Error processing timestamps in {filename}: {e}", exc_info=True)
                    continue
                except psycopg2.Error as e:
                    logging.error(f"Database error processing {filename}: {e}", exc_info=True)
                    conn.rollback()
                except Exception as e:
                    logging.error(f"Error processing file {filename}: {e}", exc_info=True)

    except psycopg2.Error as e:
        logging.error(f"Database connection error: {e}", exc_info=True)
    finally:
        # Close the cursor and connection
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
