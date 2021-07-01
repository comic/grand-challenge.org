#!/bin/bash

echo "Starting docker-compose, press Ctrl+D to cycle docker compose using a down-up cycle"
echo "Press Ctrl+C (once) to stop"
sleep 1

export GIT_COMMIT_ID=$(git describe --always --dirty)
export GIT_BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD | sed "s/[^[:alnum:]]//g")
export DOCKER_GID=$(getent group docker | cut -d: -f3)
export GRAND_CHALLENGE_HTTP_REPOSITORY_URI=public.ecr.aws/m3y0m7n5/grand-challenge/http
export GRAND_CHALLENGE_WEB_REPOSITORY_URI=public.ecr.aws/m3y0m7n5/grand-challenge/web
export GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI=public.ecr.aws/m3y0m7n5/grand-challenge/web-base
export GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI=public.ecr.aws/m3y0m7n5/grand-challenge/web-test-base

make build_web_test
make build_http

trap 'docker-compose down ; echo Stopped ; exit 0' SIGINT

make development_fixtures

docker-compose up &

while true ; do
	read Input
	if [ $? -eq 1 ]
	    then
	        docker-compose restart web
	        docker-compose restart celery_worker
	        docker-compose restart celery_worker_evaluation
	        docker-compose restart celery_beat
	fi
done
