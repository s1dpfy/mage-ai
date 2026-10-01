import base64
import io
import json
import os
from pathlib import Path
import re
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
import firebase_admin
from firebase_admin import credentials, firestore
from google import genai
from PIL import Image

# 1. 환경 변수 및 경로 설정
load_dotenv()
GEMINI_API_KEY = os.getenv("key") or os.getenv("GEMINI_API_KEY")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# 2. Firebase 시크릿 파일 경로 판별
env_admin_path = os.getenv("admin")
candidates = [
    env_admin_path,
    "/etc/secrets/serviceAccountKey.json",
    "/etc/secrets/firebase.json",
    str(BASE_DIR / "serviceAccountKey.json")
]

SECRET_KEY_PATH = None
for candidate in candidates:
    if candidate and os.path.exists(candidate):
        SECRET_KEY_PATH = candidate
        break

if not SECRET_KEY_PATH:
    raise RuntimeError(
        "❌ Firebase 인증 파일을 찾을 수 없습니다.\n"
        "'/etc/secrets/serviceAccountKey.json' 또는 프로젝트 루트의 'serviceAccountKey.json'을 확인하세요."
    )

# 3. Firebase 초기화
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(SECRET_KEY_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        raise RuntimeError(f"❌ Firebase 인증 실패: {e}")

db = firestore.client()

# 4. FastAPI 앱 설정
app = FastAPI(title="물건 가치 측정기")


# 5. HTML 라우트
@app.get("/", response_class=HTMLResponse)
async def login_page():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(f"❌ '{index_file}' 파일이 없습니다.", status_code=404)
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.post("/start", response_class=HTMLResponse)
async def start_camera_page(username: str = Form(...)):
    camera_file = TEMPLATES_DIR / "camera.html"
    if not camera_file.exists():
        return HTMLResponse(f"❌ '{camera_file}' 파일이 없습니다.", status_code=404)
    html_content = camera_file.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content.replace("{{ username }}", username))


# 6. 전체 랭킹 조회 API (상위 50위)
@app.get("/api/rankings")
async def get_rankings():
    try:
        docs = (
            db.collection("rankings")
            .order_by("price_num", direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )

        rankings = []
        for rank, doc in enumerate(docs, start=1):
            item = doc.to_dict()
            rankings.append({
                "rank": rank,
                "username": item.get("username", "익명"),
                "name": item.get("name", "미확인 물건"),
                "tag": item.get("tag", ""),
                "price": item.get("price", "0원"),
                "price_num": item.get("price_num", 0),
                "reason": item.get("reason", ""),
                "image_url": item.get("image_url", "")
            })
        return JSONResponse(content=rankings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"랭킹 조회 실패: {e}")


# 7. 이미지 감정 및 Firestore 등록 API
@app.post("/evaluate")
async def evaluate_image(
    username: str = Form(...),
    file: UploadFile = File(...)
):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API Key가 누락되었습니다.")

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # 랭킹 썸네일용 1:1 중앙 크롭 & 200x200 압축
        w, h = image.size
        min_dim = min(w, h)
        left = (w - min_dim) / 2
        top = (h - min_dim) / 2
        right = (w + min_dim) / 2
        bottom = (h + min_dim) / 2

        cropped_img = image.crop((left, top, right, bottom))
        cropped_img.thumbnail((200, 200), Image.Resampling.LANCZOS)

        img_buffer = io.BytesIO()
        cropped_img.save(img_buffer, format="JPEG", quality=80)
        base64_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{base64_str}"

        # Gemini API 전송용 경량화 (512px)
        ai_image = image.copy()
        ai_image.thumbnail((512, 512), Image.Resampling.LANCZOS)

        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = """
        사진 속 대상을 식별하고 대략적인 가치나 가격을 유쾌하고 빠르게 판정해줘.

        [판정 룰 - 엄격 준수]
        1. 사람/얼굴:
           - 아무리 잘생기고 예뻐도 절대 200만 원 초과 금지 (MAX 2,000,000원 제한).
           - 현실감 있고 킹받는 생활 밀착형 시세 책정 (예: 훈남상 180만 원, 직장인 4,500원).
        2. 일반 물건: 시중/중고 체감 시세
        3. 반려동물: 츄르 환산 가치 (최대 200만 원 선)
        4. 음식/기타: 현실적인 식당/배달 시세

        반드시 다음 JSON 형식으로만 출력하고 정수형 price_num 필드를 포함할 것:
        {
          "name": "식별 대상 요약 (예: 카페 훈남 알바상, 빈티지 머그컵, 에어팟 프로)",
          "tag": "카테고리 태그 (예: 훈남 상한가, 레트로 감성, 생활 필수품)",
          "price": "180만 원",
          "price_num": 1800000,
          "reason": "왜 이 가격인지 한 줄 이유"
        }
        """

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[ai_image, prompt],
            config={"temperature": 0.7}
        )

        raw_text = response.text.strip()
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        data = json.loads(match.group(0)) if match else json.loads(raw_text)

        # 200만 원 상한선 검증
        price_num = int(data.get("price_num", 0))
        if "사람" in data.get("tag", "") or "관상" in data.get("name", ""):
            if price_num > 2000000:
                price_num = 2000000
                data["price"] = "200만 원 (상한선)"
                data["price_num"] = 2000000

        # Firestore에 저장 (이미지 썸네일 포함)
        record = {
            "username": username,
            "name": data.get("name", "미확인"),
            "tag": data.get("tag", "미분류"),
            "price": data.get("price", "0원"),
            "price_num": price_num,
            "reason": data.get("reason", ""),
            "image_url": image_url,
            "created_at": datetime.utcnow()
        }
        db.collection("rankings").add(record)

        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
