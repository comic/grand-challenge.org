#!/usr/bin/env bash

set -e

docker build --platform=linux/amd64 -t grand-challenge-invoke .
docker image save --platform=linux/amd64 grand-challenge-invoke | gzip -c > invoke.tar.gz
