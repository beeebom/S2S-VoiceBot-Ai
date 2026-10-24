FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY meoww/ ./meoww/
COPY transcripts/ ./transcripts/

ENV MEOWW_STORE=/data/calls.jsonl
VOLUME /data

EXPOSE 8000
CMD gunicorn "meoww.webhook:create_app()" --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 120
