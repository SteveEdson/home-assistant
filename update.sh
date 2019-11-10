#!/usr/bin/env bash

git pull
docker-compose pull
docker-compose down
docker-compose up -d
docker image prune -f
docker container prune -f
