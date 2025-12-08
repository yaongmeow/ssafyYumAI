import io
import base64
import json
import os
import faiss

from PIL import Image
from openai import OpenAI


client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")
)

# 로컬 FAISS + 메타데이터 로딩
index = faiss.read_index(os.getenv("FAISS_PATH"))

with open(os.getenv("META_PATH"), "r", encoding="utf-8") as f:
    food_meta = json.load(f)


# 이미지 압축 함수
def compress_image(image_bytes, max_size=512, quality=70):
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")

    # 512px 이하로 축소
    img.thumbnail((max_size, max_size))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# 콘텐츠에서 텍스트 추출 함수
def extract_text_from_content(content):
    if content is None:
        return None

    # content가 문자열
    if isinstance(content, str):
        return content.strip()

    # content가 리스트
    if isinstance(content, list):
        texts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                texts.append(c.get("text", ""))
        return "\n".join(texts).strip() or None

    return None


# 이미지 분석 함수
def analyze_image_with_llm(client: OpenAI, image_bytes: bytes):
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    system_prompt = """
    당신은 이미지 기반 식단 분석 전문가입니다.
    이미지에 있는 음식들을 분석하여 JSON 형식으로만 응답하십시오:

    {
      "foods": [
        {"name": "<음식명>", "estimated_gram": <수치>}
      ]
    }
    설명 문장 없이 JSON만 출력하십시오.
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 사진의 음식 구성과 추정 중량을 JSON으로 제공해줘."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded}"
                        }
                    }
                ]
            }
        ],
        temperature=0.1
    )

    raw_content = resp.choices[0].message.content
    content = extract_text_from_content(raw_content)

    if not content:
        raise ValueError("LLM 분석 결과가 비어 있습니다. Vision 모델 응답을 확인하세요.")

    return json.loads(content)
