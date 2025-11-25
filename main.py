from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}


# 타겟 분석
@app.post("/target")
async def get_target():
    return


# 식단 분석
@app.post("/meal")
async def get_meal_info():
    return