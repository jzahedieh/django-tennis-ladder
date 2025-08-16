# docker/backup-sync/Dockerfile
FROM alpine:3.20

# base tools + python
RUN apk add --no-cache bash tzdata ca-certificates python3 py3-pip

# create venv and install AWS CLI v1 (works on musl/Alpine)
RUN python3 -m venv /opt/awscli \
 && /opt/awscli/bin/pip install --no-cache-dir 'awscli==1.*' \
 && ln -s /opt/awscli/bin/aws /usr/local/bin/aws

ENV TZ=Europe/London

# your script + cron
COPY backup-sync.sh /usr/local/bin/backup-sync.sh
COPY crontab /etc/crontabs/root
RUN chmod +x /usr/local/bin/backup-sync.sh

# run cron in foreground
CMD ["crond","-f","-l","2"]