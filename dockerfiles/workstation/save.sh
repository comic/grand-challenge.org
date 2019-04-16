#!/usr/bin/env bash

docker build -t workstation:latest .
docker save workstation:latest | gzip -c > workstation.tar.gz
