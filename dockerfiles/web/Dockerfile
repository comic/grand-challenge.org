###################
#  Base Container #
###################

ARG PYTHON_VERSION
ARG GDCM_VERSION_TAG
ARG POETRY_HASH

FROM grandchallenge/web-base:${PYTHON_VERSION}-${GDCM_VERSION_TAG}-${POETRY_HASH} as base

###################
#  Webpack        #
###################
FROM node:11-alpine as npm
RUN mkdir /src
COPY package.json /src/
COPY ./app/grandchallenge/core/static/css/base.scss /src/base.scss
WORKDIR /src

RUN npm install && npm run build

###################
#  Test Container #
###################
FROM base as test

# Add java and graphviz for plantuml documentation
RUN apt-get update && apt-get install -y default-jre graphviz
RUN poetry install --no-root

COPY --chown=django:django setup.cfg /home/django

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/

##################
# Dist Container #
##################
FROM base as dist

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput

ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID
