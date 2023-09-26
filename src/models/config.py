from pydantic import BaseModel, Field, typing
from bson import ObjectId
from datetime import datetime
from src.py_object_id import *

class ConfigModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    key: str
    value: typing.Any
    created_at: datetime = Field(default=None)
    updated_at: datetime = Field(default=None)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}