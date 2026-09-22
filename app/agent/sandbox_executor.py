import subprocess
import json
from app.config import get_settings

settings = get_settings()

DOCKER_TIMEOUT_SECONDS = 10  # outer safety net, on top of Postgres's own 5s statement_timeout


def run_sandboxed_query(sql: str, risk_tier: str) -> dict:
    """
    Runs `sql` inside the sandbox container, using the read-only role for
    LOW risk queries and the write role for HIGH risk queries (only ever
    called for HIGH after human approval — enforced by the caller, not here).
    """
    db_url = settings.writer_database_url if risk_tier == "HIGH" else settings.reader_database_url

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
    