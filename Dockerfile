FROM python:3.9.17-slim

ENV INSTALL_PATH /agelessaide
WORKDIR $INSTALL_PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED 1

COPY . .

RUN pip install -vvv -r requirements.txt

ENV FLASK_ENV production
ENV FLASK_APP app.py

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "3", "app:app"]

EXPOSE 8080
