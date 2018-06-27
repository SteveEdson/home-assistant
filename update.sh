#!/usr/bin/env bash

git pull
docker-compose pull
docker-compose down
docker-compose up -d