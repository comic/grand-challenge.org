FROM python:3.6

RUN apt-get update && \
    apt-get install -y \
    python-openssl \
    libpng-dev \
    libjpeg-dev \
    libjpeg62-turbo-dev \
    libfreetype6-dev \
    libxft-dev \
    libmysqlclient-dev \
    libffi-dev \
    wget \
    gettext

# We need to wait for the database to be available, which happens
# some time after the container is started. Dockerize allows us to do this.
ENV DOCKERIZE_VERSION v0.5.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

ARG PIPENV_DEV
ADD Pipfile /app/
ADD Pipfile.lock /app/
RUN python -m pip install -U pipenv
RUN pipenv install --system $PIPENV_DEV

ADD ./app /app/

ADD ./dockerfiles/web/google-analytics-tracking.js.template /tmp/google-analytics-tracking.js.template

RUN mkdir /static
