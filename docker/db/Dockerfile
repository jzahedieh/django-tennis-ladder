FROM mysql:8.0

RUN mkdir /backup
COPY docker/db/backup.sh /backup.sh
RUN chmod 0744 /backup.sh

# Oracle Linux base → microdnf + cronie
RUN microdnf -y update && microdnf -y install cronie && microdnf clean all

COPY docker/db/backup-cron /etc/cron.d/backup-cron
RUN chmod 0644 /etc/cron.d/backup-cron && crontab /etc/cron.d/backup-cron
RUN touch /var/log/cron.log

COPY docker/db/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
CMD ["mysqld"]
