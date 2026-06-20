FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Socket Mode: outbound websocket only, no ports to expose.
CMD ["python", "app.py"]
