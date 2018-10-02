#!/bin/bash

echo "Starting docker-compose, press Ctrl+D to cycle docker compose using a down-up cycle"
echo "Press Ctrl+C (once) to stop"
sleep 1

export TRAVIS_BUILD_NUMBER=$(git describe --always --dirty)

make build

trap 'docker-compose down ; echo Stopped ; exit 0' SIGINT

docker-compose up &

while true ; do
	read Input
	if [ $? -eq 1 ]
	    then
	        make build
	        docker-compose restart web
	        docker-compose restart celery_worker
	        docker-compose restart celery_worker_evaluation
	        docker-compose restart celery_beat
	fi
done
