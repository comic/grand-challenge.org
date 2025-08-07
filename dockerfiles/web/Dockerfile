# Build args used in FROM
ARG PYTHON_VERSION
ARG LOCKFILE_HASH
ARG GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI
ARG GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI

###################
# NPM Builder     #
###################
FROM ${GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS npm-builder

WORKDIR /app

COPY --chown=django:django ./app/package.json ./app/package-lock.json /app/
RUN npm ci
COPY --chown=django:django ./app/ /app/
RUN npm run build


##################
# Test Container #
##################
FROM ${GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS test

COPY --chown=django:django setup.cfg /home/django

WORKDIR /app
RUN mkdir /tmp/.pytest_cache
COPY --chown=django:django ./app/ /app/
COPY --chown=django:django --from=npm-builder /app/grandchallenge/core/static/npm_vendored/ /app/grandchallenge/core/static/npm_vendored/
COPY --chown=django:django --from=npm-builder /app/node_modules/ /app/node_modules/

##################
# Dist Container #
##################
FROM ${GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS dist

WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --chown=django:django --from=npm-builder /app/grandchallenge/core/static/npm_vendored/ /app/grandchallenge/core/static/npm_vendored/

ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID

RUN python manage.py collectstatic --noinput && python manage.py compress --force
