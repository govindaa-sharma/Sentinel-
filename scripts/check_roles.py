import psycopg2
from app.config import get_settings

settings = get_settings()


def try_write(role_name: str, conn_string: str):
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE clients SET status='inactive' WHERE id=1")
        conn.commit()
        print(f"{role_name}: write SUCCEEDED (rows affected: {cur.rowcount})")
    except Exception as e:
        conn.rollback()
        print(f"{role_name}: write BLOCKED — {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    try_write("sentinel_reader", settings.reader_database_url)
    try_write("sentinel_writer", settings.writer_database_url)

    # reset status back to active afterward, using the writer role, so our seed data stays clean
    conn = psycopg2.connect(settings.writer_database_url)
    cur = conn.cursor()
    cur.execute("UPDATE clients SET status='active' WHERE id=1")
    conn.commit()
    conn.close()
    print("Reset client 1 back to active.")