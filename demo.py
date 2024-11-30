import streamlit as st
import pandas as pd
import dspy
from db_connect import get_db_schema, connect_to_db

turbo = dspy.LM(model="gpt-4")
dspy.settings.configure(lm=turbo)

output_description = """Generated SQL query that fetches data. the column names must be 
in double quotes. make sure to re-verify the correctness of the query before giving the 
output"""

# creating a module that can generate the sql query
class UserQueryToSQL(dspy.Signature):
    user_query = dspy.InputField(desc="A natural language query about the database")
    db_schema = dspy.InputField(desc="Schema details of the database")
    sql_query = dspy.OutputField(desc=output_description)


output_description = """Generate Python code that creates a data visualization based on the user's prompt and the provided data. Ensure that the generated code uses appropriate libraries like matplotlib, seaborn, or plotly, and make sure the chart type is appropriate for the data.
Also ensure that you are providing correct axis when generating the code"""

# Create a module for generating visualization code
class UserQueryToVisualization(dspy.Signature):
    user_query = dspy.InputField(desc="A natural language query asking for a specific visualization")
    data_description = dspy.InputField(desc="A description of the dataframe, including its columns and data types")
    visualization_code = dspy.OutputField(desc=output_description)

# def generate_visualization_code(user_query, data_description):
#     """Generate Python code for visualization based on user input and data description."""
#     # Use DSPy LLM to generate the visualization code
#     prediction = dspy.ChainOfThought(UserQueryToVisualization)(
#         user_query=user_query, 
#         data_description=data_description
#     )
    
#     # Extract the generated code
#     visualization_code = prediction.visualization_code
#     return visualization_code

def generate_visualization_code(user_query, data_description):
    """Generate Python code for visualization based on user input and data description."""
    # Use DSPy LLM to generate the visualization code
    prediction = dspy.ChainOfThought(UserQueryToVisualization)(
        user_query=user_query, 
        data_description=data_description
    )
    
    # Extract the generated code
    visualization_code = prediction.visualization_code
    
    # Remove backticks or triple quotes if present
    cleaned_code = visualization_code.replace("'''", "").replace('```', "").replace("python","").replace("plt.show()", "st.pyplot(plt)")
    
    return cleaned_code

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

    except Exception as e:
        st.error(f"Error executing SQL query: {e}")
        return None

def generate_sql_query(user_query):
    # Fetch the schema from the database
    db_schema = get_db_schema()
    
    if not db_schema:
        print("Could not fetch database schema. Exiting...")
        return None

    # Convert schema dictionary to a string format that DSPy can use
    schema_description = []
    for table, columns in db_schema.items():
        # Format column names with double quotes
        quoted_columns = [f'"{column}"' for column in columns]
        schema_description.append(f"Table: {table}, Columns: {', '.join(quoted_columns)}")
    schema_context = "\n".join(schema_description)

    # Generate the SQL query using DSPy, passing the schema as context
    prediction = dspy.ChainOfThought(UserQueryToSQL)(user_query=user_query, db_schema=schema_context)

    # Extract the generated SQL query
    sql_query = prediction.sql_query
    # print("Internal DSPy prompt:")
    # print(turbo.inspect_history(n=1))
    return sql_query

def get_data_description(df):
    """Generate a description of the dataframe, including column names and data types."""
    description = []
    for col in df.columns:
        description.append(f"{col} ({df[col].dtype})")
    return ", ".join(description)

def execute_generated_code(code, df):
    """Safely execute the LLM-generated Python code."""
    try:
        # Prepare a local environment for executing the generated code
        local_vars = {"df": df, "st": st, "pd": pd}
        
        # Execute the code in the local environment
        exec(code, {}, local_vars)
    except Exception as e:
        st.error(f"Error executing generated code: {e}")

# Streamlit App
st.title("LLM-Powered SQL Query and Data Visualization")

# Get user input
user_query = st.text_input("Enter your query in natural language (e.g., 'Show me a bar chart of top 10 sales')")


if user_query:
    # Run the SQL query (hard-coded or generated via LLM)
    sql_query = generate_sql_query(user_query)  # Assume this function exists to generate the query

    if sql_query:
        # Display the generated SQL query in Streamlit
        st.write("Generated SQL Query:")
        st.code(sql_query, language='sql')  # Displays the SQL query in code block format
        
    # Execute the SQL query and fetch the results
    df = run_sql_query(sql_query)

    if df is not None:
        st.write("Query Results:")
        st.dataframe(df)

        # Generate a description of the data
        data_description = get_data_description(df)

        # Generate the visualization code using an LLM
        st.write("Generating visualization...")
        visualization_code = generate_visualization_code(user_query, data_description)

        if visualization_code:
            st.code(visualization_code, language="python")

            # Execute the generated code to display the visualization
            execute_generated_code(visualization_code, df)