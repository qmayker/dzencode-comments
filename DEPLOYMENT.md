# Production deployment

The Compose stack uses Nginx as its only public-facing service. Nginx serves
collected static files and uploaded media from separate Docker volumes, sends
regular HTTP requests to Gunicorn, and proxies `/ws/` WebSocket connections to
Daphne. PostgreSQL stores application data; Redis backs the cache, Channels,
Celery, and the event listener.

## Configure and start

1. Copy `.env.example` to `.env`. Set `SECRET_KEY` to a new random value (for
   example, run `python -c "import secrets; print(secrets.token_urlsafe(64))"`)
   and set `DB_PASSWORD` to a strong database password. Set `ALLOWED_HOSTS` to
   the public hostnames and `CSRF_TRUSTED_ORIGINS` to their full origins,
   including `https://` when using HTTPS. Keep `.env` private.
2. Terminate HTTPS at a trusted proxy in front of this stack and configure that
   proxy to redirect HTTP traffic to HTTPS. The included Nginx listener is
   HTTP-only and forwards the `X-Forwarded-Proto` value received from that proxy.
   Keep `SECURE_SSL_REDIRECT=True` and `SECURE_HSTS_SECONDS` enabled so Django
   also enforces HTTPS when it sees the trusted proxy's forwarded scheme.
   Production session and CSRF cookies are marked secure. Restrict access to
   `HTTP_PORT` (default 80) so clients can reach it only through the trusted proxy.
3. Reply notification emails use Django's console backend and are written to
   the output of the process that runs the Celery task.
4. Build and start the services:

   ```sh
   docker compose up --build -d
   ```

The web container applies database migrations and collects static files before
starting Gunicorn. Daphne, Nginx, Celery, and the event listener start after the
web service is healthy. Only Nginx publishes a host port; PostgreSQL and Redis
are accessible only on the private Compose network.

This stack initializes a new PostgreSQL database; `migrate` creates its schema
but does not copy data from the development SQLite database. If existing
comments or uploaded files must be kept, migrate the database and copy the
media files into the persistent volumes before directing traffic to this stack.

To create an administrator account:

```sh
docker compose exec web python manage.py createsuperuser
```

## Local HTTPS

For browser testing on `https://localhost`, create a self-signed certificate and
start the HTTPS proxy alongside the normal Compose stack:

```sh
python scripts/create_local_tls_cert.py
docker compose -f compose.yml -f compose.local-https.yml up --build -d
```

Open [https://localhost](https://localhost). Since this certificate is
self-signed and not installed as a trusted root, the browser will show a
certificate warning; accept it only for local development. The private key and
certificate are stored in the ignored `certs/` directory. To replace them, run
`python scripts/create_local_tls_cert.py --force`, then restart the stack.

## Persistent data

Back up the `postgres_data` and `media` Docker volumes. Uploaded files are
stored in `media` and served directly by Nginx; collected application assets
are stored separately in `staticfiles` and can be recreated by running
`docker compose restart web`. Redis data is persisted in `redis_data`; it is
runtime state and does not replace database or media backups.

Do not use `docker compose down -v` for routine deployment: it removes the
database, Redis, media, and static-file volumes.
