#!/usr/bin/env bash

git pull
docker-compose pull
docker-compose stop homeassistant
docker-compose up -d --build --remove-orphans homeassistant
docker-compose up -d --build --remove-orphans appdaemon
docker-compose up -d --build --remove-orphans db
docker-compose up -d --build --remove-orphans ma
docker-compose up -d --build --remove-orphans whisper
docker-compose up -d --build --remove-orphans piper
docker image prune -f
docker container prune -f
