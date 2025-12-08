from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    age: int = Field(..., example=27)
    gender: str = Field(..., example="male")
    height: float = Field(..., example=175.0)
    weight: float = Field(..., example=70.0)
