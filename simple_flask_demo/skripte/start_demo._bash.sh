#!/bin/bash

cd ..
docker build -t sapl-flask-demo:latest .
docker-compose up