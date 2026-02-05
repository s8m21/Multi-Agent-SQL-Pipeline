import tiktoken
import logging
import re
import json

def num_tokens_from_message(message, model_name):
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        logging.warning(f"Model {model_name} not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    tokens_per_message = 3
    content = message.get('content') or str(message)
    return tokens_per_message + len(encoding.encode(content))

def num_tokens_from_messages(messages, model_name):
    return sum(num_tokens_from_message(m, model_name) for m in messages)

def truncate_messages(messages, model_name, max_tokens=112000):
    truncated = messages.copy()
    while num_tokens_from_messages(truncated, model_name) > max_tokens and len(truncated) > 1:
        truncated.pop(0)
    return truncated

def chunk_message(message: str, max_tokens: int, model_name: str) -> list:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        logging.warning(f"Model {model_name} not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    tokens = encoding.encode(message)
    chunks = []
    while tokens:
        chunk_tokens = tokens[:max_tokens]
        chunks.append(encoding.decode(chunk_tokens))
        tokens = tokens[max_tokens:]
    return chunks

def extract_json_from_markdown(text: str) -> dict:
    """
    Extracts a JSON dictionary from a markdown or code block if present.
    """
    # Pattern 1: Python code block
    match = re.search(r"```python\s*({.*?})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
            
    # Pattern 2: Raw JSON-like bracket
    match = re.search(r"({.*})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
            
    # Pattern 3: SQL code block (fallback for when LLM only returns SQL)
    sql_match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    if sql_match:
        return {"sql_query": sql_match.group(1).strip()}
        
    return {}
