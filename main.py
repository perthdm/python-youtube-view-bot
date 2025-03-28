import requests
from fastapi_utils.tasks import repeat_every
from src.models.email import *
from src.models.proxy import *
from src.models.config import *
from src.models.bot import *
from src.models.viewer import *
from src.models.task import *
from src.datetime import *
from src.load_files import *
from datetime import datetime
from dotenv import load_dotenv
from worker import viewer, celery
from typing import Optional, List
from random import randint, choice
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Body, HTTPException, status, Request
import os
import pymongo
import math
import json
import dns.resolver
import certifi

ca = certifi.where()


app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGODB_CONNECTION_URI = os.environ.get("MONGODB_CONNECTION_URI")

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

client = pymongo.MongoClient(MONGODB_CONNECTION_URI, tlsCAFile=ca)
db = client["youtube_viewer"]
views_per_task = 5


@app.get("/")
def hello_world():
    return JSONResponse(status_code=status.HTTP_200_OK, content="Hello World")


@app.get("/bot", response_model=List[BotModel])
async def get_bots():
    bots = list(db["bots"].find().sort("start_time", -1))
    bots_json_data = json.dumps(bots, cls=DateTimeEncoder)
    return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(bots_json_data))


@app.post("/bot")
async def create_bot(bot: BotModel = Body(...)):
    global views_per_task
    bot = jsonable_encoder(bot)

    if bot["target_views"] < views_per_task:
        views_per_task = bot["target_views"]

    total_tasks = math.ceil(bot["target_views"]/views_per_task)
    bot["total_tasks"] = total_tasks
    bot["start_time"] = datetime.now()
    created_bot = db["bots"].insert_one(bot)
    created_bot_id = str(created_bot.inserted_id)

    for i in range(total_tasks):
        proxy_list = list(db["proxies"].find({"status": 1}))
        proxy = proxy_list[i % len(proxy_list)]

        task = jsonable_encoder(
            TaskModel(
                bot_id=created_bot_id,
                proxy=proxy,
                views=views_per_task,
            )
        )

        # print("TASK -----> ", task)

        t = viewer.delay(created_bot_id, views_per_task, proxy,
                         bot["video_url"], bot["keywords"], bot["video_title"], bot["filter"])
        task["_id"] = t.id
        db["tasks"].insert_one(task)

    result = {
        "success": True,
        "message": "Successfully",
        "bot_id": created_bot_id
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@app.get("/bot/{bot_id}")
def get_bot(bot_id):
    bot = db["bots"].find_one({"_id": bot_id})
    bots_json_data = json.dumps(bot, cls=DateTimeEncoder)
    return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(bots_json_data))


@app.delete("/bot/{bot_id}")
def delete_bot(bot_id):
    tasks = list(db["tasks"].find({"bot_id": bot_id}))
    for task in tasks:
        celery.control.revoke(task["_id"])

    db["bots"].update_one(
        {"_id": bot_id},
        {"$set":
            {
                "status": 4,
                "finish_time": datetime.now()
            }
         }
    )

    result = {
        "success": True,
        "message": "Successfully"
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@app.get("/config/{key}", response_model=ConfigModel)
async def get_config(key):
    config = db["configs"].find_one({"key": key})
    config_json_data = json.dumps(config, cls=DateTimeEncoder)
    return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(config_json_data))


@app.post("/config")
async def create_config(config: ConfigModel = Body(...)):
    config = jsonable_encoder(config)
    is_exist = db["configs"].find_one({"key": config["key"]})
    if is_exist == None:
        config["created_at"] = datetime.now()
        config["updated_at"] = datetime.now()
        _ = db["configs"].insert_one(config)
    else:
        _ = db["configs"].update_one(
            {"key": config["key"]},
            {"$set":
                {
                    "value": config["value"],
                    "updated_at": datetime.now()
                }
             }
        )
    result = {
        "success": True,
        "message": "Successfully"
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@app.get("/configs", response_model=List[ConfigModel])
async def get_configs():
    configs = list(db["configs"].find())
    return JSONResponse(status_code=status.HTTP_200_OK, content=configs)


@app.post("/proxy")
def create_proxy(proxy: ProxyModel = Body(...)):
    proxy = jsonable_encoder(proxy)
    created_proxy = db["proxies"].insert_one(proxy)
    result = {
        "success": True,
        "message": "Successfully",
        "id": created_proxy.inserted_id
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@app.get("/proxy", response_model=List[ProxyModel])
def get_proxies():
    proxies = list(db["proxies"].find())
    return JSONResponse(status_code=status.HTTP_200_OK, content=proxies)


@app.post("/email")
def create_email(email: EmailModel = Body(...)):
    email = jsonable_encoder(email)
    created_email = db["emails"].insert_one(email)
    result = {
        "success": True,
        "message": "Successfully",
        "id": created_email.inserted_id
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@app.get("/email", response_model=List[EmailModel])
def get_emails():
    emails = list(db["emails"].find())
    return JSONResponse(status_code=status.HTTP_200_OK, content=emails)


@app.delete("/email/{email_id}")
def delete_email(email_id):
    db["emails"].delete_one({"_id": email_id})

    result = {
        "success": True,
        "message": "Successfully"
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@app.on_event("startup")
@repeat_every(seconds=5, wait_first=True)
def periodic():
    print("Hello World.")
    url = os.environ.get("API_ENDPOINT")+"/watcher/order"

    payload = {}
    headers = {'bot-token': BOT_TOKEN}

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 200:
        # print(response.text)
        create_order(response.text)


def create_order(bot):
    global views_per_task
    try:

        # bot_running = db["bots"].find_one(
        #     {"$or": [{"status": 0}, {"status": 1}]})

        # if bot_running:
        #     print("Running")
        # else:
        bot = json.loads(bot)
        # bot: BotModel = bot

        bot['status'] = 0
        bot['completed_tasks'] = 0
        bot['total_tasks'] = 0
        bot['target_viewed'] = 0

        if bot["target_views"] < views_per_task:
            views_per_task = bot["target_views"]

        total_tasks = math.ceil(bot["target_views"]/views_per_task)
        bot["total_tasks"] = total_tasks
        bot["start_time"] = datetime.now()

        have_bot = db["bots"].count_documents({"watch_id": bot["watch_id"]})

        if have_bot <= 0:
            created_bot = db["bots"].insert_one(bot)
            created_bot_id = str(created_bot.inserted_id)

            for i in range(total_tasks):
                proxy_list = list(db["proxies"].find({"status": 1}))
                proxy = proxy_list[i % len(proxy_list)]

                task = jsonable_encoder(
                    TaskModel(
                        bot_id=created_bot_id,
                        proxy=proxy,
                        views=views_per_task,
                    )
                )

                t = viewer.delay(created_bot_id, views_per_task, proxy,
                                 bot["video_url"], bot["keywords"], bot["video_title"], bot["filter"])
                task["_id"] = t.id
                db["tasks"].insert_one(task)
    except Exception as e:
        print("Error:", e)


@app.on_event("startup")
@repeat_every(seconds=10, wait_first=True)
def set_order_status():
    bots = list(db["bots"].find({"status": {"$ne": 0}}))
    try:
        for bot in bots:
            url = os.environ.get("API_ENDPOINT")+"/watcher/set-bot-status"
            payload = json.dumps(bot, cls=DateTimeEncoder)
            headers = {
                'Content-Type': 'application/json',
                'bot-token': BOT_TOKEN
            }

            response = requests.post(url, headers=headers, data=payload)

    except Exception as e:
        print("Error:", e)


@app.on_event("startup")
@repeat_every(seconds=5, wait_first=True)
def bot_count():
    bots = list(db["bots"].find().sort("start_time", -1))

    for bot in bots:
        url = os.environ.get("API_ENDPOINT")+"/watcher/bot-count"
        payload = json.dumps(bot, cls=DateTimeEncoder)
        headers = {
            'Content-Type': 'application/json',
            'bot-token': BOT_TOKEN
        }

        response = requests.request("POST", url, headers=headers, data=payload)
