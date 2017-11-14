#!/bin/bash

docker-compose run web dockerize -wait tcp://db:3306 -timeout 30s bash -c "py.test --cov-report= --cov=." 

mv app/.coverage .coverage.docker
 
exit $(docker inspect -f '{{.State.ExitCode}}' $(docker ps -aqf name=comicdjango_web_run_1))

