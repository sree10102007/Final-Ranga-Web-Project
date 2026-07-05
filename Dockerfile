FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY goat_farm_app/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY goat_farm_app /app/goat_farm_app

EXPOSE 5001

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "goat_farm_app.Project_goatfarm:app"]
