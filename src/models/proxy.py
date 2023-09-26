from pydantic import BaseModel, Field, typing
from bson import ObjectId
from src.py_object_id import *

class ProxyModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    index: int
    type: str
    url: str
    port: str
    is_auth: bool = True
    username: str
    password: str
    status: int = 1 # 0 = Inactive, 1 = Active

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}