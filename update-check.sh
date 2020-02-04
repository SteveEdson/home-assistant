#!/usr/bin/env bash

docker run --rm -it -v $(pwd):/usr/src/app -w /usr/src/app node:lts-alpine "npm install && update-check.js"