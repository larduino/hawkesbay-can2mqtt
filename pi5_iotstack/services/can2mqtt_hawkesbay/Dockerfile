FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY can2mqtt_hbay.py .

CMD ["python3", "can2mqtt_hbay.py"]
