###################
#  Base Container #
###################
FROM python:3.8 as base

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
    gettext \
    libvips-dev

ENV PYTHONUNBUFFERED 1

RUN mkdir -p /opt/poetry /app /static /opt/static
RUN python -m pip install -U "pip!=20.0"
RUN python -m pip install -U poetry

RUN groupadd -g 2001 -r django && useradd -m -u 2001 -r -g django django
RUN chown django:django /opt/poetry /app /static /opt/static
USER django:django

# Install base python packages
WORKDIR /opt/poetry
COPY poetry.toml /opt/poetry
COPY pyproject.toml /opt/poetry
COPY poetry.lock /opt/poetry
RUN poetry install --no-dev --no-root
ENV PATH="/opt/poetry/.venv/bin:$PATH"

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

RUN poetry install --no-root
COPY --chown=django:django setup.cfg /home/django

WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput

##################
# Dist Container #
##################
FROM base as dist

WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput
