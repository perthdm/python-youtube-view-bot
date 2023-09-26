from pydantic import BaseModel, Field, typing
from bson import ObjectId
from datetime import datetime
from src.py_object_id import *

class BotModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    video_title: str
    keywords: list
    video_url: str
    target_views: int
    target_viewed: int = 0
    status: int = 0 # 0 = PENDING, 1 = RUNNING, 2 = SUCCESS, 3 = FAILED, 4 = CANCELED
    minimum: float
    maximum: float
    filter: str = ''
    total_tasks: int = 0
    completed_tasks: int = 0
    save_bandwidth: bool = False
    start_time: datetime = Field(default=None)
    finish_time: datetime = Field(default=None)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}