# Используем базовый образ Python
FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
