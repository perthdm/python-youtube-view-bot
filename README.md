# youtube-viewer-server

1. Create an environment (python -m venv venv)
2. Activate environment 
    - Windows (.\venv\Scripts\activate)
    - MacOS (source ./venv/bin/activate)
3. Install dependencies from requirements.txt file (pip install -r requirements.txt)
4. Create .env file
- API
run: uvicorn main:app --reload
- Worker
run: celery -A worker.celery worker -P gevent --loglevel=info