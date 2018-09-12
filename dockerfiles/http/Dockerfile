FROM nginx:1.15.2

RUN apt-get update && \
    apt-get install -y \
    gettext

RUN useradd -u 2001 cwww

RUN openssl dhparam -out /etc/ssl/private/dhparams.pem 2048

ADD mime.types /etc/nginx/mime.types
ADD nginx.conf.template /tmp/nginx.conf.template
