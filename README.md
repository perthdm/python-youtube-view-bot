python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

python -m celery -A worker.celery worker -P gevent --loglevel=info

install requiremnet first
