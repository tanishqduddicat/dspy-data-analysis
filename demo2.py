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

output_description = """Generate Python code that creates a data visualization based on the user's prompt and the provided data. Ensure that the generated code uses appropriate libraries like matplotlib, seaborn, or plotly, and make sure the chart type is appropriate for the data."""

# Create a module for generating visualization code
class UserQueryToVisualization(dspy.Signature):
    user_query = dspy.InputField(desc="A natural language query asking for a specific visualization")
    data_description = dspy.InputField(desc="A description of the dataframe, including its columns and data types")
    visualization_code = dspy.OutputField(desc=output_description)

def generate_visualization_code(user_query, data_description, columns, chart_type):
    """Generate Python code for visualization based on user input, data description, selected columns, and chart type."""
    query_with_selection = f"{user_query} using columns {', '.join(columns)} with the following chart types: {chart_type}"
    prediction = dspy.ChainOfThought(UserQueryToVisualization)(
        user_query=query_with_selection, 
        data_description=data_description
    )
    
    visualization_code = prediction.visualization_code
    cleaned_code = visualization_code.replace("'''", "").replace('```', "").replace("python","").replace("plt.show()", "st.pyplot(plt)")
    
    return cleaned_code

def run_sql_query(sql_query):
    """Execute the generated SQL query on the database."""
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        cursor.close()
        connection.close()
        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {e}")
        return None

def generate_sql_query(user_query):
    db_schema = get_db_schema()
    if not db_schema:
        print("Could not fetch database schema. Exiting...")
        return None

    schema_description = [f"Table: {table}, Columns: {', '.join([f'\"{col}\"' for col in columns])}" for table, columns in db_schema.items()]
    schema_context = "\n".join(schema_description)

    prediction = dspy.ChainOfThought(UserQueryToSQL)(user_query=user_query, db_schema=schema_context)
    sql_query = prediction.sql_query
    return sql_query

def get_data_description(df):
    return ", ".join([f"{col} ({df[col].dtype})" for col in df.columns])

def execute_generated_code(code, df):
    try:
        local_vars = {"df": df, "st": st, "pd": pd}
        exec(code, {}, local_vars)
    except Exception as e:
        st.error(f"Error executing generated code: {e}")

# Streamlit App
st.title("LLM-Powered SQL Query and Data Visualization")

user_query = st.text_input("Enter your query in natural language (e.g., 'Show me a bar chart of top 10 sales')")

if user_query:
    sql_query = generate_sql_query(user_query)
    if sql_query:
        st.write("Generated SQL Query:")
        st.code(sql_query, language='sql')
        
    df = run_sql_query(sql_query)

    if df is not None:
        st.write("Query Results:")
        st.dataframe(df)

        data_description = get_data_description(df)

        # Step 1: Prompt for visualization
        st.write("What would you like to visualize from this data?")
        user_display_query = st.text_input("Enter your visualization prompt")

        # Step 2: Multi-select for columns
        selected_columns = st.multiselect("Select columns to include in the visualization:", options=df.columns.tolist())

        # Step 3: Multi-select for chart type
        chart_types = chart_types = [
            "Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram", 
            "Box Plot",         # Great for identifying outliers and spread of data
            "Violin Plot",      # Shows density and outliers, useful for comparison
            "Heatmap",          # Useful for correlations and patterns
            "Density Plot",     # Good for visualizing the distribution, similar to KDE plot
            "Pair Plot",        # Useful for visualizing relationships and outliers across multiple variables
            "Swarm Plot",       # Shows individual points with some jitter, useful for small datasets
            "Bubble Chart",     # Enhanced scatter plot with size encoding for a third variable
            "Area Chart",       # Useful for showing cumulative data over time
            "Hexbin Plot"       # Specialized scatter plot for high-density data, helps detect clusters and outliers
        ]
        selected_chart_type = st.multiselect("Select a chart types:", options=chart_types)

        if user_display_query and selected_columns and selected_chart_type:
            st.write("Generating visualization...")

            visualization_code = generate_visualization_code(user_display_query, data_description, selected_columns, selected_chart_type)

            if visualization_code:
                st.code(visualization_code, language="python")
                execute_generated_code(visualization_code, df)
