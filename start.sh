#!/bin/bash
source ./venv/Scripts/activate
celery -A worker.celery worker -P gevent --loglevel=info