#!/bin/bash

echo "Starting docker-compose, press Ctrl+D to cycle docker compose using a down-up cycle"
echo "Press Ctrl+C (once) to stop"
sleep 1

export GIT_COMMIT_ID=$(git describe --always --dirty)
export GIT_BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD | sed "s/[^[:alnum:]]//g")
export DOCKER_GID=$(getent group docker | cut -d: -f3)

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
