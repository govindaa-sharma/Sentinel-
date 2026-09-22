import os
import sys
import json
import psycopg2

def main():
    sql = os.environ.get("SENTINEL_SQL")
    conn_string = os.environ.get("SENTINEL_DB_URL")

    if not sql or not conn_string:
        print(json.dumps({"error": "Missing SQL or DB URL"}))
        sys.exit(1)

    try:
        conn = psycopg2.connect(conn_string, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '5000'")  # 5 seconds, in ms
        cur.execute(sql)

        if cur.description:  # SELECT-style query, has rows to fetch
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            conn.commit()
            print(json.dumps({"success": True, "rows": result, "rowcount": len(result)}, default=str))
        else:  # UPDATE/DELETE/INSERT, no rows to fetch, but has rowcount
            conn.commit()
            print(json.dumps({"success": True, "rows": [], "rowcount": cur.rowcount}))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()