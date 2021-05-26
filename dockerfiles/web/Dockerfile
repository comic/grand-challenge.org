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

USER django:django
WORKDIR /app
RUN mkdir /tmp/.pytest_cache
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/

##################
# Dist Container #
##################
FROM ${GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${POETRY_HASH} as dist

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput

ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID
