# Whatnot's Cross Listing App

Publishes listings to multiple market places and publishes events and call webhooks

## How to run
 ```bash
 python -m aiohttp.web -H localhost -P 5000 app.server:run
 ```

## How to run migrations
```bash
alembic revision -m "Comments"
```

Edit the generated file and run the upgrade command
```bash
alembic upgrade head
```
