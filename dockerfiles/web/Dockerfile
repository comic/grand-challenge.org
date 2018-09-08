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

RUN mkdir -p /app /static /dbox/Dropbox/media
WORKDIR /app

ARG PIPENV_DEV
ADD Pipfile /app/
ADD Pipfile.lock /app/
RUN python -m pip install -U pipenv
RUN pipenv install --system $PIPENV_DEV

RUN chown 2001:2001 /app /static /dbox/Dropbox/media

USER 2001:2001

ADD ./app /app/
