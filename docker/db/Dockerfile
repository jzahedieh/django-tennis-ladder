FROM mysql:8.0

# 1) MySQL tuning
# ensure any previous mistaken directory is gone
RUN rm -rf /etc/mysql/conf.d/zz-tuning.cnf && \
    mkdir -p /etc/mysql/conf.d && \
    cat > /etc/mysql/conf.d/zz-tuning.cnf <<'EOF'
[mysqld]
innodb_buffer_pool_size=4G
innodb_log_file_size=512M
innodb_flush_method=O_DIRECT
innodb_flush_log_at_trx_commit=1
max_connections=200
EOF

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
