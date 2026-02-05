def format_result_for_ui(result: dict) -> str:
    parts = []

    # 1. Routed Agent Label
    agent = result.get("agent")
    if agent:
        parts.append(f"Routed to: `{agent.capitalize()} Agent`")

    # 2. Explanation
    explanation = result.get("explanation")
    if explanation:
        parts.append(f"Insight:\n> {explanation.strip()}")

    # 3. SQL Query Block
    sql_query = result.get("sql_query")
    if sql_query:
        parts.append("SQL Query:")
        parts.append(f"```sql\n{sql_query.strip()}\n```")

    # 4. Table
    headers = result.get("headers", [])
    rows = result.get("rows", [])
    if rows and headers:
        table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |"
        ]
        for row in rows:
            if isinstance(row, dict):
                table.append("| " + " | ".join(str(row.get(h, row.get(h.lower(), ""))) for h in headers) + " |")
            elif isinstance(row, (tuple, list)):
                table.append("| " + " | ".join(str(cell) for cell in row) + " |")
        parts.append("\n".join(table))

    # 6. Error
    if result.get("error"):
        parts.append(f"Error: {result['error']}")

    return "\n\n".join(parts)
