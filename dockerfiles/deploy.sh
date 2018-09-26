#!/bin/bash

echo "$DOCKER_PASSWORD" | docker login --username grandchallenge --password-stdin

docker push grandchallenge/http:"$TRAVIS_BUILD_NUMBER"
docker push grandchallenge/web:"$TRAVIS_BUILD_NUMBER"
