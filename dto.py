from pydantic import BaseModel


class TargetCreateDto(BaseModel):
    gender: str
    weight: float
    height: float
    age: int


class TargetDto(BaseModel):
    calorise: float
    protein: float
    fat: float
    carbonhydrate: float


class FoodAnalyzeDto(BaseModel):
    image_base64: str


class FoodDto(BaseModel):
    food_name: str
    weight: int