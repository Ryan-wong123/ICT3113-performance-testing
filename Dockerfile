FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV TICKETS_DB_PATH=/app/runtime/tickets.db
ENV REQUEST_LOG_PATH=/app/logs/requests.jsonl

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
