release: alembic upgrade head
web: gunicorn app.server:run --worker-class aiohttp.GunicornWebWorker
orders: python pull.py
relist: python relist.py
