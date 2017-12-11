FROM nginx:mainline

RUN apt-get update && \
    apt-get install -y \
    gettext

RUN useradd -u 2001 cwww

RUN openssl dhparam -out /etc/ssl/private/dhparams.pem 2048

ADD nginx.conf.template /tmp/nginx.conf.template
