from pydantic import BaseModel, Field, typing
from bson import ObjectId
from src.py_object_id import *

class EmailModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    password: str
    status: int = 1 # 0 = Inactive, 1 = Active, 2 = Running

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}