FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY comments/ /app/
COPY --from=frontend-build /app/comments/commenting/static/commenting/dist/ \
    /app/commenting/static/commenting/dist/

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /app/media /app/staticfiles /app/logs \
    && chown -R app:app /app

USER app
