``` markdown
# SSL Certificate Setup for Oracle Cloud Infrastructure

## Manual Certificate Generation

The docker-compose certbot service is configured for renewals only. For initial certificate generation, use this standalone command:
```
bash docker run --rm -it
-p 80:80
-v (pwd)/data/certbot/conf:/etc/letsencrypt \ -v(pwd)/data/certbot/www:/var/www/certbot
certbot/certbot:latest
certonly --standalone
--email your-email@domain.com
--agree-tos
--no-eff-email
--verbose
-d your-domain.com
``` 

## Post-Generation Steps

1. **Fix permissions**:
   ```bash
   sudo chown -R $USER:$USER ./data/certbot/conf/
   ```

2. **Create DH parameters**:
   ```bash
   curl https://ssl-config.mozilla.org/ffdhe2048.txt -o ./data/certbot/conf/ssl-dhparams.pem
   ```

3. **Start application**:
   ```bash
   docker compose -f docker-compose.prod.oci.yml up -d
   ```

## Why Manual Generation?

The docker-compose certbot service has this entrypoint which only handles renewals:
```
yaml entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
``` 

This is why you get "No renewals were attempted" when trying to use it for initial certificate generation.
```
