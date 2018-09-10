#!/bin/bash

trap 'docker-compose down ; echo Stopped ; exit 0' SIGINT

echo "Starting docker-compose, press Ctrl+D to cycle docker compose using a down-up cycle"
echo "Press Ctrl+C (once) to stop"
sleep 1

docker-compose up --build &

while true ; do 
	read Input
	if [ $? -eq 1 ]
	    then
	        docker-compose restart web
	        docker-compose restart celery_worker
	        docker-compose restart celery_beat
	fi
done

