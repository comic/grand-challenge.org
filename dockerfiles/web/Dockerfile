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

RUN mkdir -p /app /static /dbox/Dropbox/media
WORKDIR /app

ARG PIPENV_DEV
ADD Pipfile /app/
ADD Pipfile.lock /app/
RUN python -m pip install -U pipenv
RUN pipenv install --system

RUN chown 2001:2001 /static /dbox/Dropbox/media

USER 2001:2001

ADD --chown=2001:2001 ./app/config /app/config
ADD --chown=2001:2001 ./app/grandchallenge /app/grandchallenge
ADD --chown=2001:2001 ./app/manage.py /app/


FROM base as test
USER root
ARG PIPENV_DEV
RUN pipenv install --system $PIPENV_DEV
USER 2001:2001
ADD --chown=2001:2001 ./app/tests /app/tests
ADD --chown=2001:2001 ./app/pytest.ini /app/
