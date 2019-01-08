#!/bin/bash

echo "Starting docker-compose, press Ctrl+D to cycle docker compose using a down-up cycle"
echo "Press Ctrl+C (once) to stop"
sleep 1

export TRAVIS_BUILD_NUMBER=$(git describe --always --dirty)
export TRAVIS_BRANCH=$(git rev-parse --abbrev-ref HEAD | sed "s/[^[a-zA-Z0-9]]//")

make build

trap 'docker-compose down ; echo Stopped ; exit 0' SIGINT

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
