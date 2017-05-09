FROM nginx:mainline

RUN apt-get update && \
    apt-get install -y \
    gettext

ADD nginx.conf.template /tmp/nginx.conf.template
