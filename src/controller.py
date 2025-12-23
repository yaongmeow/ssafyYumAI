import json

import numpy as np
from fastapi import UploadFile, File, APIRouter

from src.dto import UserInfo
from src.utils import client, index, food_meta, compress_image, analyze_image_with_llm

router = APIRouter()


@router.post("/recommend")
def recommend(user: UserInfo):
    system_prompt = """
    당신은 영양학 전문가입니다.
    입력으로 나이, 성별, 키(cm), 몸무게(kg)가 주어지면
    다이어트를 위해 준수해야 하는 하루 권장 칼로리(kcal), 단백질(g), 탄수화물(g), 지방(g)을 계산해
    아래 JSON 형식만 반환하십시오.
    
    {
      "calories": <정수 또는 소수>,
      "protein": <정수 또는 소수>,
      "carbohydrate": <정수 또는 소수>,
      "fat": <정수 또는 소수>
    }
    
    설명이나 여분의 텍스트는 절대 포함하지 마십시오.
    """

    user_prompt = f"""
    나이: {user.age}
    성별: {user.gender}
    키: {user.height}cm
    몸무게: {user.weight}kg
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    result_text = response.choices[0].message.content.strip()
    result = json.loads(result_text)

    return result


@router.post("/diet")
async def diet_analysis(file: UploadFile = File(...)):
    raw_bytes = await file.read()

    # Step 1: 이미지 압축 적용
    img_bytes = compress_image(raw_bytes, max_size=512, quality=70)

    # Step 2: Vision 모델로 음식 분석
    parsed = analyze_image_with_llm(client, img_bytes)

    results = []

    # Step 3: 음식명 임베딩 + FAISS 검색
    for item in parsed["foods"]:
        name = item["name"]
        estimated_gram = item["estimated_gram"]

        # 텍스트 임베딩 -> FAISS 검색
        resp = client.embeddings.create(
            model="text-embedding-3-large",
            input=name
        )
        vec = np.array(resp.data[0].embedding).astype("float32")
        vec = vec.reshape(1, -1)

        distances, indices = index.search(vec, 1)

        idx = indices[0][0]
        dist = distances[0][0]

        meta = food_meta[idx]

        # results.append({
        #     "detected_food": name,
        #     "estimated_gram": estimated_gram,
        #     "matched_food": meta,
        #     # "similarity_distance": float(dist)
        # })
        meta["quantity"] = estimated_gram
        results.append(meta)
        print(meta)

    # return {"result": results}
    return results


@router.post("/diet/recommend")
async def recommend_diet():
    # 식단 추천 기능
    ...
