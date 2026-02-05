import os
import uuid
import pandas as pd
import logging
from typing import Annotated, List, Any, Union
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
import re

repl = PythonREPL()

# Ensure CHARTS_DIR is defined relative to the project structure
CHARTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "charts"))
os.makedirs(CHARTS_DIR, exist_ok=True)

@tool
def python_repl(
    code: Annotated[str, "The python code to execute to generate your chart."],
    sql_query: Annotated[str, "The sql query to form the dataframe to be used as df in python code."],
    filename: Annotated[str, "The ABSOLUTE filename path to save the chart."]
):
    """Use this to execute python code for visualization."""
    if not sql_query:
        return "Error: SQL query parameter is required."

    filename = filename.replace("\\", "/") 

    try:
        # Ensure Agg backend for headless plotting
        if "matplotlib.use('Agg')" not in code:
            code = "import matplotlib; matplotlib.use('Agg')\n" + code

        # Create directory if it doesn't exist
        chart_dir = os.path.dirname(filename)
        if chart_dir and not os.path.exists(chart_dir):
            os.makedirs(chart_dir, exist_ok=True)

        # Patch code to use the correct savefig path
        code = re.sub(r".*plt\.savefig\(.*\)", "", code)
        code += f"\nplt.savefig(r'{filename}')"

        result = repl.run(code)
        return result

    except Exception as e:
        logging.error(f"Execution FAILED inside python_repl: {repr(e)}")
        return f"Failed to execute. Error: {repr(e)}"

@tool
def get_unique_filename(a: int = 0):
    """
    Use this to get a unique filename for charts.
    Returns the FULL, ABSOLUTE path to the chart file.
    """
    unique_name = str(uuid.uuid4()) + ".png"
    return os.path.normpath(os.path.join(CHARTS_DIR, unique_name))

def save_rows_to_csv(rows: List[Any], headers: List[str]) -> Union[str, None]:
    """
    Saves the provided rows and headers to a temporary CSV file.
    """
    try:
        unique_name = str(uuid.uuid4()) + ".csv"
        csv_filename = os.path.normpath(os.path.join(CHARTS_DIR, unique_name))
        
        os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
        
        df = pd.DataFrame(rows, columns=headers)
        df.to_csv(csv_filename, index=False)
        return csv_filename
    except Exception as e:
        logging.error(f"Failed to save temp CSV: {e}")
        return None
