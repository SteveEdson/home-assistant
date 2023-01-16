#!/usr/bin/env bash

git pull
docker-compose pull
docker-compose down homeassistant
docker-compose up -d --build --remove-orphans homeassistant
docker-compose up -d --build --remove-orphans appdaemon
docker-compose up -d --build --remove-orphans db
docker image prune -f
docker container prune -f
