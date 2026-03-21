FROM python:3.11-slim

WORKDIR /app

COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

COPY . .

RUN mkdir -p static/screenshots database

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV DISABLE_AI=true

EXPOSE 8000

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:8000", "--timeout", "120", "app:app"]
