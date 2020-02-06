release: alembic upgrade head
web: gunicorn app.server:run --bind localhost:8000 --worker-class aiohttp.GunicornWebWorker
