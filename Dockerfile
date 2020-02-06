FROM python:3.7-alpine

RUN apk update && \
    apk add --virtual build-deps gcc python-dev musl-dev && \
    apk add postgresql-dev
RUN apk add --no-cache openssl-dev libffi-dev
RUN apk add --no-cache jpeg-dev zlib-dev
RUN apk add --update curl gcc g++

RUN pip install --upgrade pip
RUN pip install psycopg2

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./entrypoint.sh /
ENTRYPOINT ["sh", "/entrypoint.sh"]

COPY . /app
WORKDIR /app

EXPOSE 8000
