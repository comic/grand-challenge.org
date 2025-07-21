# Build args used in FROM
ARG PYTHON_VERSION
ARG LOCKFILE_HASH
ARG GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI
ARG GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI

##################
# Test Container #
##################
FROM ${GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS test

COPY --chown=django:django setup.cfg /home/django

WORKDIR /app
RUN mkdir /tmp/.pytest_cache
COPY --chown=django:django ./app/ /app/
RUN npm ci && npm run dev
##################
# Dist Container #
##################
FROM ${GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS dist

WORKDIR /app
COPY --chown=django:django ./app/ /app/
RUN npm ci && npm run build
ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID

RUN python manage.py collectstatic --noinput && python manage.py compress --force
