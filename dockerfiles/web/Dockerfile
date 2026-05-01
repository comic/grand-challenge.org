# Build args used in FROM
ARG PYTHON_VERSION
ARG LOCKFILE_HASH
ARG GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI
ARG GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI

##################
# Test Container #
##################
FROM --platform=linux/amd64 ${GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS test

COPY --chown=django:django setup.cfg /home/django

WORKDIR /app
RUN mkdir /tmp/.pytest_cache
COPY --chown=django:django ./app/ /app/

##################
# Dist Container #
##################
FROM --platform=linux/amd64 ${GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI}:${PYTHON_VERSION}-${LOCKFILE_HASH} AS dist

WORKDIR /app
COPY --chown=django:django ./app/ /app/

ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID

RUN python manage.py collectstatic --noinput && GRAND_CHALLENGE_USE_LOC_MEM_CACHE=true python manage.py compress --force

####################
# Lambda Container #
####################

FROM --platform=linux/amd64 dist AS dist-lambda

ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "lambda_tasks.handler.handler" ]
