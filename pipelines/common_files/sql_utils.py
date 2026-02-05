import re
from typing import List, Tuple, Any, Union

def clean_sql_query(query: str) -> str:
    return re.sub(r'\s+', ' ', query).strip().rstrip("`").rstrip(":")

def extract_sql_query(text: str) -> str:
    pattern = re.compile(r'(?i)(select.*?)(?=\n\d+\.\s+|$|````)', re.DOTALL)
    matches = pattern.findall(text)
    return [clean_sql_query(m) for m in matches]

def extract_column_names_from_sql(sql_query: str) -> list:
    """
    Extracts clean column aliases or names from the SELECT clause of the SQL query.
    """
    match = re.search(r'select\s+(.*?)\s+from', sql_query, re.IGNORECASE | re.DOTALL)
    if not match:
        return []

    columns_str = match.group(1)
    columns = [col.strip() for col in re.split(r',(?![^()]*\))', columns_str)]

    cleaned = []
    for col in columns:
        # Handle alias: AS "alias" or AS alias
        as_match = re.search(r'\s+AS\s+"?([\w\d_]+)"?', col, re.IGNORECASE)
        if as_match:
            cleaned.append(as_match.group(1))
        else:
            # Fallback: take last part after . or space
            col = col.strip('" ')
            if '.' in col:
                col = col.split('.')[-1]
            cleaned.append(col.strip('" '))
    return cleaned

def execute_sql_safe(db, sql_query: str) -> Tuple[List[str], List[Any], Union[str, None]]:
    """
    Executes a SQL query safely and returns (headers, rows, error_message).
    Standardizes the result format from SQLAlchemy/LangChain.
    """
    try:
        result = db._execute(sql_query)
        if isinstance(result, list):
            headers = extract_column_names_from_sql(sql_query)
            rows = result
        else:
            # Handle standard SQLAlchemy Result/Cursor outcomes
            headers = getattr(result, "columns", [])
            # Convert keys() to list if it's a legacy object, or use .keys()
            if not isinstance(headers, list) and hasattr(headers, "keys"):
                headers = list(headers.keys())
            
            rows = getattr(result, "rows", result)
            
        return headers, rows, None
    except Exception as e:
        return [], [], str(e)
