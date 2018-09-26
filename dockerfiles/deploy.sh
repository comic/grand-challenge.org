#!/bin/bash

TAG=$(git log -1 --pretty=%h)

docker tag grand-challengeorg_http grandchallenge/http:"$TAG"

echo "$DOCKER_PASSWORD" | docker login --username grandchallenge --password-stdin

docker push grandchallenge/http:"$TAG"
