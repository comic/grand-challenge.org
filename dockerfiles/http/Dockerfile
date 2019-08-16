FROM nginx:1.16.1

RUN apt-get update && \
    apt-get install -y \
    gettext

RUN useradd -u 2001 cwww

COPY dhparams.pem /etc/ssl/private/dhparams.pem
COPY mime.types /etc/nginx/mime.types
COPY nginx.conf.template /tmp/nginx.conf.template
