import pytest
from pipelines.common_files.sql_utils import clean_sql_query, extract_column_names_from_sql
from pipelines.common_files.llm_utils import extract_json_from_markdown

def test_clean_sql_query():
    query = "  SELECT * FROM test;  "
    assert clean_sql_query(query) == "SELECT * FROM test;"

def test_extract_column_names():
    sql = 'SELECT name, age AS "UserAge", dept_id FROM users'
    cols = extract_column_names_from_sql(sql)
    assert "name" in cols
    assert "UserAge" in cols
    assert "dept_id" in cols

def test_extract_json_from_markdown():
    text = """Here is the result:
```python
{"sql_query": "SELECT 1", "explanation": "test"}
```
"""
    result = extract_json_from_markdown(text)
    assert result["sql_query"] == "SELECT 1"
    assert result["explanation"] == "test"
