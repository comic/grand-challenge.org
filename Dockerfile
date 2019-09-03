FROM python:3.6

RUN apt-get update && \
    apt-get install -y \
    python-openssl \
    libpng-dev \
    libjpeg-dev \
    libjpeg62-turbo-dev \
    libfreetype6-dev \
    libxft-dev \
    libffi-dev \
    wget \
    gettext

ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app /static

WORKDIR /app

# Install base python packages
ADD requirements.txt /app
ADD requirements.dev.txt /app
RUN pip install -r requirements.txt && pip install -r requirements.dev.txt

RUN chown 2001:2001 /static

USER 2001:2001

ADD --chown=2001:2001 ./app/ /app/
RUN python manage.py collectstatic