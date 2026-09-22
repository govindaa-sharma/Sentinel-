FROM python:3.11-slim

RUN pip install --no-cache-dir psycopg2-binary

WORKDIR /sandbox
COPY run_query.py .

# Run as a non-root user — if anything ever escaped the script's logic,
# it still wouldn't have root privileges inside the container
RUN useradd -m sandboxuser
USER sandboxuser

ENTRYPOINT ["python", "run_query.py"]