#!/bin/bash

cd /srv/ResearchInteractionSupportEnviroment

git pull origin main

docker compose down
docker compose build
docker compose up -d --force-recreate

docker system prune -f
