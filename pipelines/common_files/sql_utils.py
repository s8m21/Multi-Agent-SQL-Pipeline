import os
import re
from typing import List, Tuple, Any, Union, Optional


def clean_sql_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip().rstrip("`").rstrip(":")


def extract_sql_query(text: str) -> List[str]:
    pattern = re.compile(r"(?i)(select.*?)(?=\n\d+\.\s+|$|````)", re.DOTALL)
    matches = pattern.findall(text)
    return [clean_sql_query(m) for m in matches]


def extract_column_names_from_sql(sql_query: str) -> list:
    """
    Extracts clean column aliases or names from the SELECT clause of the SQL query.
    """
    match = re.search(r"select\s+(.*?)\s+from", sql_query, re.IGNORECASE | re.DOTALL)
    if not match:
        return []

    columns_str = match.group(1)
    columns = [col.strip() for col in re.split(r",(?![^()]*\))", columns_str)]

    cleaned = []
    for col in columns:
        as_match = re.search(r'\s+AS\s+"?([\w\d_]+)"?', col, re.IGNORECASE)
        if as_match:
            cleaned.append(as_match.group(1))
        else:
            col = col.strip('" ')
            if "." in col:
                col = col.split(".")[-1]
            cleaned.append(col.strip('" '))
    return cleaned


def _get_max_rows() -> int:
    """Returns maximum number of rows allowed from a query result."""
    try:
        return int(os.getenv("SQL_MAX_ROWS", "1000"))
    except ValueError:
        return 1000


def validate_sql_query(sql_query: str) -> Optional[str]:
    """
    Basic read-only validation for generated SQL.

    - Requires SELECT/CTE-style read queries.
    - Blocks destructive keywords.
    """
    if not sql_query:
        return "Empty SQL query is not allowed."

    normalized = sql_query.strip().lstrip("(")
    lowered = normalized.lower()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        return "Only read-only SELECT queries are allowed."

    forbidden_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "truncate",
        "alter",
        "create",
        "merge",
        "grant",
        "revoke",
    ]
    pattern = r"\b(" + "|".join(forbidden_keywords) + r")\b"
    if re.search(pattern, lowered):
        return "Destructive or DDL SQL statements are not allowed."

    return None


def execute_sql_safe(db, sql_query: str) -> Tuple[List[str], List[Any], Union[str, None]]:
    """
    Executes a SQL query safely and returns (headers, rows, error_message).
    Standardizes the result format from SQLAlchemy/LangChain.
    """
    cleaned_query = clean_sql_query(sql_query)

    validation_error = validate_sql_query(cleaned_query)
    if validation_error:
        return [], [], validation_error

    max_rows = _get_max_rows()

    try:
        result = db._execute(cleaned_query)
        if isinstance(result, list):
            headers = extract_column_names_from_sql(cleaned_query)
            rows = result[:max_rows]
        else:
            headers = getattr(result, "columns", [])
            if not isinstance(headers, list) and hasattr(headers, "keys"):
                headers = list(headers.keys())

            rows_obj = getattr(result, "rows", result)
            try:
                rows = list(rows_obj)[:max_rows]
            except TypeError:
                rows = rows_obj

        return headers, rows, None
    except Exception:
        # Do not expose raw DB errors to the caller.
        return [], [], "Database error occurred while executing the query."
