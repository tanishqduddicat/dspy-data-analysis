import os
import psycopg2
import pandas as pd

# this fucntion is used to connect with the database
def connect_to_db():
    try:
        # Retrieve database credentials from environment variables
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')

        # Create a connection using psycopg2
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None
    


# this function is used to fetch the schema of the connected database
def get_db_schema():
    conn = connect_to_db()
    if conn is None:
        print("Connection failed.")
        return {}

    try:
        # Query to fetch all tables and their columns from the information schema
        query = """
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        """

        cursor = conn.cursor()
        cursor.execute(query)

        # Fetch all results
        schema = cursor.fetchall()

        # Structure the schema as a dictionary {table_name: [column_name1, column_name2, ...]}
        db_schema = {}
        for table, column in schema:
            if table not in db_schema:
                db_schema[table] = []
            db_schema[table].append(column)

        # Close the cursor and connection
        cursor.close()
        conn.close()

        return db_schema
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return {}
    

# for running the sql querry generated to fetch the results
def run_sql_query(sql_query):
    """Execute the generated SQL query on the database."""
    try:
        # Establish a database connection (adjust connection details as needed)
        connection = connect_to_db()
        cursor = connection.cursor()

        # Execute the query
        cursor.execute(sql_query)

        # Fetch all results
        rows = cursor.fetchall()

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Convert results to a DataFrame
        df = pd.DataFrame(rows, columns=columns)

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return df

    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        return None