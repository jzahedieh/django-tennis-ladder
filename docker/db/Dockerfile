
FROM mysql:8.0

# backup setup
RUN mkdir /backup
COPY docker/db/backup.sh /backup.sh
RUN chmod 0744 /backup.sh

# cron setup - Oracle Linux uses microdnf
RUN microdnf update -y
RUN microdnf install -y cronie

COPY docker/db/backup-cron /etc/cron.d/backup-cron
RUN chmod 0644 /etc/cron.d/backup-cron
RUN crontab /etc/cron.d/backup-cron
RUN touch /var/log/cron.log

COPY docker/db/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

CMD ["mysqld"]