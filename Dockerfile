FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn

COPY . .

RUN pip install --no-cache-dir .

RUN mkdir -p /data /tmp

ENV LANDING_PAGE_DIR=/app/static
ENV DB_PATH=/data/referral_engine.db

EXPOSE 3000

CMD ["sh", "-c", "uvicorn src.referral_engine.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
