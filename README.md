# ssafyYumAI

간단 설명
- ssafyYumAI는 음식 이미지와 사용자 정보를 기반으로 영양 분석 및 음식 추천을 제공하는 FastAPI 기반 서비스입니다.
- OpenAI(또는 호환 LLM)를 통해 이미지 기반 음식 인식 및 영양 계산을 수행하고, 텍스트 임베딩 + FAISS로 데이터베이스의 음식 메타와 매칭합니다.

목차
- 요구사항
- 프로젝트 구조
- 환경 변수
- 설치 및 실행 (로컬 / Docker)
- API 사용법 (예시 요청)
- 데이터(벡터/메타) 설명
- 아키텍처(텍스트 다이어그램)
- 향후 개선 제안
- 부록: .env.example

---

요구사항
- Python 3.12
- 필요한 패키지: `requirements.txt`에 명시됨 (FastAPI, uvicorn, openai, faiss-cpu, pillow, numpy, pydantic 등)
- 로컬에 FAISS 인덱스와 메타 JSON 파일 필요 (`vector/food_index.faiss`, `vector/food_meta.json`)
- 환경변수: `LLM_API_KEY`, `LLM_BASE_URL`(선택), `FAISS_PATH`, `META_PATH`

프로젝트 구조 (요약)
- `main.py`
  - FastAPI 앱 엔트리포인트. `src.controller`의 라우터를 포함.
- `src/`
  - `controller.py` : API 라우트 구현 (`/recommend`, `/diet`)
  - `dto.py` : Pydantic 모델 정의 (`UserInfo`)
  - `utils.py` : OpenAI 클라이언트, FAISS 인덱스/메타 로드, 이미지 압축/분석 유틸
- `vector/`
  - `food_index.faiss` : FAISS 인덱스 파일
  - `food_meta.json` : 각 인덱스에 대응하는 음식 메타 데이터(영양소 등)
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`

환경 변수
- `LLM_API_KEY` (필수) : LLM(예: OpenAI) API 키
- `LLM_BASE_URL` (선택) : 자체 호스팅 OpenAI 호환 엔드포인트 사용 시
- `FAISS_PATH` (필수) : FAISS 인덱스 파일 경로. 예: `./vector/food_index.faiss`
- `META_PATH` (필수) : 메타 JSON 경로. 예: `./vector/food_meta.json`

설치 및 실행

1) 로컬 (가상환경 권장)
- macOS / zsh 예시:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 환경변수 설정(예: export LLM_API_KEY=your_key ...)
export LLM_API_KEY="your_api_key"
export LLM_BASE_URL=""             # 필요 시
export FAISS_PATH="./vector/food_index.faiss"
export META_PATH="./vector/food_meta.json"
uvicorn main:app --host 0.0.0.0 --port 8000
```

2) Docker
- 이미지를 빌드해서 실행:
```bash
docker build -t ssafy-yumai:latest .
docker run -e LLM_API_KEY="$LLM_API_KEY" \
           -e LLM_BASE_URL="$LLM_BASE_URL" \
           -e FAISS_PATH="/app/vector/food_index.faiss" \
           -e META_PATH="/app/vector/food_meta.json" \
           -p 8000:8000 ssafy-yumai:latest
```
- docker-compose (개발 모드, reload 포함):
```bash
# .env에 필요한 값들을 넣고
docker-compose up --build
```

API 사용법

1) POST /recommend
- 설명: 사용자 정보(나이/성별/키/몸무게)를 받아 LLM으로 영양 권장(칼로리/단백질/탄수/지방)을 계산하여 JSON으로 반환.
- 요청 예시:
```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 27,
    "gender": "male",
    "height": 175.0,
    "weight": 70.0
  }'
```
- 응답 예시(예상 형태):
```json
{
  "calorie": 2500,
  "protein_g": 80,
  "carb_g": 300,
  "fat_g": 70
}
```
(LLM 출력에 따라 필드명/값이 달라질 수 있음)

2) POST /diet
- 설명: 음식 사진을 업로드하면 이미지 분석(LLM vision)으로 음식명을 추출, 각 음식명을 임베딩하여 FAISS에서 가장 유사한 항목을 찾아 매칭된 메타 및 유사도(distance)를 반환.
- 요청 예시:
```bash
curl -X POST "http://localhost:8000/diet" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/food.jpg;type=image/jpeg"
```
- 응답 예시(예상 형태):
```json
{
  "result": [
    {
      "detected_food": "김치찌개",
      "estimated_gram": 350,
      "matched_food": {
        "name": "김치찌개",
        "kcal": 200,
        "protein_g": 10,
        "carb_g": 15,
        "fat_g": 12
      },
      "similarity_distance": 0.12345
    }
  ]
}
```
- 참고: `analyze_image_with_llm`는 LLM이 반환하는 콘텐츠에서 JSON 문자열을 추출하여 `json.loads`로 파싱합니다. LLM이 정확한 JSON을 반환하도록 system_prompt가 강제되어 있으므로 응답 포맷에 주의하세요.

데이터(벡터/메타) 설명
- `vector/food_index.faiss`
  - 텍스트 임베딩(모델: text-embedding-3-large)으로 생성된 벡터를 저장한 FAISS 인덱스 파일입니다.
  - `utils.py`에서 `faiss.read_index(FAISS_PATH)`로 로드됩니다.
- `vector/food_meta.json`
  - FAISS 인덱스의 각 벡터에 대응하는 메타 정보 배열입니다. (예: 음식명, 1인분 칼로리, 영양소 등)
  - `utils.py`에서 `json.load`로 읽어 `food_meta` 리스트로 사용됩니다.
- 주의: 인덱스와 메타의 길이/정렬이 정확히 일치해야 합니다.

아키텍처 (텍스트 형태)
- 간단한 흐름:
  - Client -> FastAPI( main.py )
    - /recommend -> OpenAI Chat Completion (system + user prompt) -> JSON 파싱 -> 반환
    - /diet
      1) 업로드 이미지 -> compress_image -> LLM Chat Completion(이미지 포함) -> detect foods (JSON)
      2) parsed foods -> OpenAI Embeddings -> FAISS search -> match meta -> 결과 반환
- 텍스트 다이어그램:
```
[Client]
   |
   v
[FastAPI app (main.py)]
   |-- /recommend --> [OpenAI Chat API] --> JSON -> Response
   |
   |-- /diet ------> [compress_image] -> [OpenAI Chat API (vision)] -> parsed foods
                     parsed foods -> [OpenAI Embeddings API] -> [FAISS index search] -> match meta
                                                          |
                                                          v
                                                    [vector/food_meta.json]
```

향후 개선 제안 (우선순위 순)
1. 에러 핸들링 및 검증 강화
   - 현재 LLM 응답을 바로 `json.loads`로 파싱함. LLM이 유효한 JSON을 반환하지 않을 경우 예외 발생. 응답 검증/재요청/포맷 정제 로직 추가 필요.
2. 메타데이터/인덱스 동기화와 검증 엔드포인트
   - FAISS 인덱스와 메타 파일이 일치하는지 확인하는 헬스 체크 엔드포인트 또는 start-up 검증 로직 추가.
3. 로컬 테스트 및 유닛 테스트 추가
   - utils 함수(이미지 압축, extract_text_from_content, analyze_image_with_llm에 대한 mock 테스트) 및 controller 엔드포인트에 대한 통합 테스트 작성.
4. 성능/스케일링: 벡터 검색 분리
   - 대량 데이터 운영 시 FAISS를 별도 벡터 DB(Weaviate, Milvus, Redis Vector 등)로 분리하고 검색 레이턴시를 모니터링.
5. 보안 및 시크릿 관리
   - 환경변수를 직접 노출하지 말고 `.env` + `.env.example` 또는 시크릿 매니저(aws/gcp/secret manager) 사용 권장.
6. LLM 호출 비용/성능 절감
   - 이미지 분석 전 간단한 CV 기반(예: YOLO)를 추가해 후보 음식명을 줄이거나, 텍스트 임베딩을 캐시하여 Embedding API 호출 최소화.

부록: .env.example (권장)
```
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=            # 필요 시
FAISS_PATH=./vector/food_index.faiss
META_PATH=./vector/food_meta.json
```

품질 및 제약사항(요약)
- 현재 제공된 코드 베이스에 unit-test 또는 CI 구성이 없음.
- `vector/food_meta.json` 파일은 로컬에 필요하며 너무 커서 전체 내용을 자동 분석할 수 없었습니다(도구 제한). README 예시는 일반적 구조에 기반해 작성되었습니다. 실제 필드명이 다르면 README의 예시 JSON을 맞춰 수정하세요.

문의 / 다음 단계 제안
- README를 리포지토리에 바로 덮어쓰기 완료했습니다. 추가로 `.env.example` 파일을 실제로 생성하거나, `vector/food_meta.json`의 샘플(몇 줄)을 제공해주시면 README의 예시 응답 스펙을 더 정확히 맞춰 드리겠습니다.

