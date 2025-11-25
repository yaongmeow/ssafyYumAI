from fastapi import FastAPI, UploadFile
from openai import OpenAI
import psycopg
import json
import os
from dto import TargetCreateDto, FoodAnalyzeDto

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}


# 타겟 분석
@app.post("/target")
async def get_target(req: TargetCreateDto):
    prompt = """
        음식 이미지를 보고 음식명과 대략적인 그램수를 JSON으로 반환하세요.
        예시:
        {"items":[{"name":"닭가슴살","amount_g":150}]}
        """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "JSON으로만 답하세요."},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image_b64}"}
                ]
            }
        ]
    )

    return json.loads(res.choices[0].message.content)
    return


# 식단 분석


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()
client = OpenAI(api_key=OPENAI_API_KEY)



# ===== STEP 1: Vision 모델 분석 =====


# ===== STEP 2: pgvector 검색 =====
def get_embedding(text: str):
    emb = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return emb.data[0].embedding


def search_food(food_name: str):
    emb = get_embedding(food_name)

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            SELECT food_name, calories, protein, fat, carbs, sodium
            FROM foods
            ORDER BY embedding <-> %s
            LIMIT 1
            """,
            (emb,)
        ).fetchone()

    if not row:
        return None

    return {
        "food_name": row[0],
        "calories": float(row[1]),
        "protein": float(row[2]),
        "fat": float(row[3]),
        "carbs": float(row[4]),
        "sodium": float(row[5])
    }


# ===== STEP 3: 100g 기준 영양 → amount_g 기준으로 계산 =====
def scale(base, amount):
    ratio = amount / 100

    return {
        "name": base["food_name"],
        "amount_g": amount,
        "calories": base["calories"] * ratio,
        "protein": base["protein"] * ratio,
        "fat": base["fat"] * ratio,
        "carbs": base["carbs"] * ratio,
        "sodium": base["sodium"] * ratio
    }


# ===== STEP 4: LLM 요약 =====
def summarize(items):
    prompt = f"""
    다음은 음식별 영양 분석입니다.
    {json.dumps(items, ensure_ascii=False)}
    한국어로 자연스럽게 설명하세요.
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content


# ===== 최종 API =====
@app.post("/meal")
def analyze(req: FoodAnalyzeDto):
    # 1. 이미지 분석 → 음식 리스트
    prompt = """
        음식 이미지를 보고 음식명과 대략적인 그램수를 JSON으로 반환하세요.
        예시:
        {"items":[{"name":"닭가슴살","amount_g":150}]}
        """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "JSON으로만 답하세요."},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{req.image_b64}"}
                ]
            }
        ]
    )

    vision_result = json.loads(res.choices[0].message.content)

    items = vision_result["items"]

    final_items = []
    total = 0

    # 2. DB 검색 + 영양 계산
    for item in items:
        base = search_food(item["name"])
        if not base:
            continue

        scaled = scale(base, item["amount_g"])
        total += scaled["calories"]
        final_items.append(scaled)

    # 3. 자연어 요약
    summary = summarize(final_items)

    return {
        "total_calories": total,
        "items": final_items,
        "summary": summary
    }
