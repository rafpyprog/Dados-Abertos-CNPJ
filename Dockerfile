FROM python:alpine3.6

RUN apk update \
    && apk add g++ \
               make \
               python3-dev


COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /cnpj

EXPOSE 8001
