#!/bin/bash

trap 'docker-compose down ; echo Stopped ; exit 0' SIGINT


echo "Starting docker-compose, press Ctrl+D to cycle docker compose using a down-up cycle"
echo "Press Ctrl+C (once) to stop"
sleep 1

while true ; do 
	docker-compose up --build & cat 
	docker-compose restart web
	docker-compose restart celery_worker
	docker-compose restart celery_beat
done

