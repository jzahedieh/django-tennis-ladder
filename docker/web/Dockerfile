FROM python:3.12-slim-bookworm

# Stream logs instead of buffer
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get -y install python3-dev default-libmysqlclient-dev build-essential pkg-config

RUN pip install --upgrade pip
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt
ADD . /code/