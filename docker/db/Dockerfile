FROM mariadb:10.1

# backup setup
RUN mkdir /backup
COPY docker/db/backup.sh .
RUN chmod 0744 /backup.sh

# cron setup
RUN apt-get update && apt-get -y install cron
COPY docker/db/backup-cron /etc/cron.d/backup-cron
RUN chmod 0644 /etc/cron.d/backup-cron
RUN crontab /etc/cron.d/backup-cron
RUN touch /var/log/cron.log

COPY docker/db/entrypoint.sh /usr/local/bin/
ENTRYPOINT ["entrypoint.sh"]

CMD ["mysqld"]
