# Build args used in FROM
ARG PYTHON_VERSION
ARG POETRY_HASH
ARG GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI
ARG GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI

#############
# Vendor JS #
#############
FROM node:11-alpine as npm
RUN mkdir /src
COPY package.json /src/
COPY ./app/grandchallenge/core/static/css/base.scss /src/base.scss
WORKDIR /src

RUN npm install && npm run build

##################
# Test Container #
##################
FROM ${GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${POETRY_HASH} as test

COPY --chown=django:django setup.cfg /home/django

WORKDIR /app
RUN mkdir /tmp/.pytest_cache
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/

##################
# Dist Container #
##################
FROM ${GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${POETRY_HASH} as dist

WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/

# Django 4.0 checks for files that are often missing from
# distributions, hack away this error by adding empty source maps
RUN mkdir -p \
      /opt/static/vendored/sentry-browser/ \
      /opt/static/vendored/uppy/packages/uppy/dist/ \
      /opt/static/vendored/vega/ \
      /opt/static/vendored/jsoneditor/ \
    && touch \
      /opt/static/vendored/sentry-browser/bundle.min.js.map \
      /opt/static/vendored/sentry-browser/bundle.js.map \
      /opt/static/vendored/uppy/packages/uppy/dist/uppy.min.js.map \
      /opt/static/vendored/vega/vega.min.js.map \
      /opt/static/vendored/jsoneditor/jsoneditor.map

RUN python manage.py collectstatic --noinput

ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID
