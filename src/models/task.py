from pydantic import BaseModel, Field, typing
from bson import ObjectId
from src.py_object_id import *
from src.models.proxy import *

class TaskModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    bot_id: str
    proxy: ProxyModel
    status: int = 0 # 0 = PENDING, 1 = RUNNING, 2 = SUCCESS, 3 = FAILED
    description: str = ""
    views: int
    viewed: int = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
