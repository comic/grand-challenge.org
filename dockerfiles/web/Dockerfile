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

RUN mkdir -p /opt/pipenv /app /static /opt/static /dbox/Dropbox/media
RUN python -m pip install -U pip
RUN python -m pip install -U pipenv

# Install base python packages
WORKDIR /opt/pipenv
COPY Pipfile /opt/pipenv
COPY Pipfile.lock /opt/pipenv
RUN pipenv install --system

RUN groupadd -g 2001 -r django && useradd -u 2001 -r -g django django

RUN chown django:django /app /static /opt/static /dbox/Dropbox/media

###################
#  Webpack        #
###################
FROM node:11-alpine as npm
RUN mkdir /src
COPY package.json /src/
WORKDIR /src

RUN npm install && npm run build

###################
#  Test Container #
###################
FROM base as test

WORKDIR /opt/pipenv
RUN pipenv install --system --dev

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput
COPY --chown=django:django pyproject.toml /tmp/pyproject.toml

##################
# Dist Container #
##################
FROM base as dist

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput
