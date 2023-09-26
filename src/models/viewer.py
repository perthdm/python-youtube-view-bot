from pydantic import BaseModel, Field, typing
from bson import ObjectId
from datetime import datetime
from src.py_object_id import *

class ViewerModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    task_id: str
    position: int
    video_duration: int = 0
    watching_duration: int = 0
    status: int = 0 # 0 = PENDING, 1 = RUNNING, 2 = SUCCESS, 3 = FAILED
    description: str = ""
    start_time: datetime = Field(default=None)
    finish_time: datetime = Field(default=None)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}