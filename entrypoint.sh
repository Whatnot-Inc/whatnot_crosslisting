#!/bin/bash

alembic upgrade head

gunicorn app.server:run --bind localhost:8000 --worker-class aiohttp.GunicornWebWorker
# python -m aiohttp.web -H localhost -P 5000 app.server:run
