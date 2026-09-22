import subprocess
import json
import psycopg2
from app.config import get_settings

settings = get_settings()

DOCKER_TIMEOUT_SECONDS = 10  # outer safety net, on top of Postgres's own 5s statement_timeout


def run_sandboxed_query(sql: str, risk_tier: str) -> dict:
    """
    Runs `sql` using the read-only role for LOW risk queries and the write role
    for HIGH risk queries (only ever called for HIGH after human approval —
    enforced by the caller, not here).

    Uses the Docker sandbox locally (real process/resource isolation on top of
    the DB-role boundary). Falls back to a direct connection when SANDBOX_MODE=direct
    (e.g. on Render, which doesn't support Docker-in-Docker) — the DB-role security
    boundary is identical either way; only the container isolation layer differs.
    """
    db_url = settings.writer_database_url if risk_tier == "HIGH" else settings.reader_database_url

    if settings.sandbox_mode == "direct":
        return _run_direct(sql, db_url)
    return _run_docker(sql, db_url)


def _run_docker(sql: str, db_url: str) -> dict:
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-e", f"SENTINEL_SQL={sql}",
                "-e", f"SENTINEL_DB_URL={db_url}",
                "--memory=128m", "--cpus=0.5",
                "--network=bridge",
                "sentinel-sandbox",
            ],
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Query exceeded {DOCKER_TIMEOUT_SECONDS}s timeout"}

    if result.returncode != 0 and not result.stdout.strip():
        return {"success": False, "error": result.stderr.strip() or "Unknown sandbox error"}

    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"success": False, "error": f"Could not parse sandbox output: {result.stdout}"}


def _run_direct(sql: str, db_url: str) -> dict:
    conn = None
    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '5000'")
        cur.execute(sql)

        if cur.description:
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            conn.commit()
            return {"success": True, "rows": rows, "rowcount": len(rows)}

        conn.commit()
        return {"success": True, "rows": [], "rowcount": cur.rowcount}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()