FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED 1

# Install app dependencies + cron
RUN apt-get update && \
    apt-get -y install python3-dev default-libmysqlclient-dev build-essential pkg-config cron && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN mkdir /code
WORKDIR /code

ADD requirements.txt /code/
RUN pip install -r requirements.txt

ADD . /code/

# Copy cron job definition
COPY docker/web/subscription-cron /etc/cron.d/subscription-cron
RUN chmod 0644 /etc/cron.d/subscription-cron && \
    crontab /etc/cron.d/subscription-cron

# Create cron log file
RUN touch /var/log/subscription.log

# Copy entrypoint
COPY docker/web/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]
