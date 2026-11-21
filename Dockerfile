FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8010
# one process: the game state (tables, players) lives in memory
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--ws-ping-interval", "15", "--ws-ping-timeout", "15"]
