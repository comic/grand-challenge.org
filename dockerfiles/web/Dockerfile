###################
#  Base Container #
###################
FROM python:3.6 as base

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

RUN mkdir -p /opt/pipenv /app /static /dbox/Dropbox/media
RUN python -m pip install -U pip
RUN python -m pip install -U pipenv

# Install base python packages
WORKDIR /opt/pipenv
ADD Pipfile /opt/pipenv
ADD Pipfile.lock /opt/pipenv
RUN pipenv install --system

RUN chown 2001:2001 /static /dbox/Dropbox/media

USER 2001:2001
WORKDIR /app

ADD --chown=2001:2001 ./app/config /app/config
ADD --chown=2001:2001 ./app/grandchallenge /app/grandchallenge
ADD --chown=2001:2001 ./app/manage.py /app/

###################
#  Test Container #
###################
FROM base as test

USER root
WORKDIR /opt/pipenv
ARG PIPENV_DEV_FLAG
RUN pipenv install --system $PIPENV_DEV_FLAG

USER 2001:2001
WORKDIR /app
ADD --chown=2001:2001 ./app/tests /app/tests
ADD --chown=2001:2001 ./app/pytest.ini /app/
