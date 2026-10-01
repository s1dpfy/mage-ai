# 📦 물건 가치 측정기 (AI Item Value Estimator)

스마트폰 카메라나 웹캠으로 물건(또는 사람, 반려동물 등)을 촬영하면, AI가 즉석에서 대상의 가치(가격)를 유쾌하게 감정해 주는 웹 서비스입니다. 감정된 결과는 실시간으로 '명예의 전당(랭킹)'에 등록되어 다른 사람들이 측정한 기발하고 재미있는 결과들과 순위를 겨룰 수 있습니다.

**🔗 라이브 데모:** [https://mage-ai-0bw6.onrender.com/start](https://mage-ai-0bw6.onrender.com/start)

---

## ✨ 주요 기능 (Features)

*   **📷 실시간 카메라 촬영:** 웹 및 모바일 환경 지원. 기기의 전/후면 카메라 전환 기능을 제공합니다.
*   **🤖 AI 즉석 감정:** Google Gemini API를 활용하여 사진 속 대상을 식별하고, 센스 있고 킹받는(?) 이유와 함께 가격을 산정합니다.
*   **🏆 명예의 전당 (실시간 랭킹):** 측정된 가치(가격)를 기준으로 상위 50개의 결과를 실시간으로 조회할 수 있습니다.
*   **⚖️ 유쾌한 자체 룰 적용:** 사람이나 얼굴을 인식할 경우 아무리 뛰어나도 절대 **200만 원을 초과할 수 없는 상한선**을 두어 소소한 재미를 제공합니다. 반려동물은 '츄르' 가치로 환산하기도 합니다.
*   **⚡ 이미지 최적화:** 서버 전송 전 이미지 크기를 리사이징(512x512)하여 빠른 처리 속도와 API 비용을 절감합니다.

---

## 🛠️ 기술 스택 (Tech Stack)

**Backend:**
*   Python 3.x
*   [FastAPI](https://fastapi.tiangolo.com/): 빠르고 가벼운 비동기 웹 프레임워크
*   [Google GenAI API](https://ai.google.dev/): 이미지 비전 분석 및 텍스트(JSON) 생성 (`gemini-3.8-flash` 모델 사용)
*   [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup): Firestore DB 연동 및 랭킹 데이터 저장
*   Pillow (PIL): 이미지 경량화 및 리사이징

**Frontend:**
*   HTML5 / CSS3 / Vanilla JavaScript
*   `navigator.mediaDevices.getUserMedia` API (웹 카메라 제어)

---

## 🚀 로컬 실행 방법 (Installation & Setup)

### 1. 저장소 클론 및 패키지 설치
```bash
git clone <repository-url>
cd <repository-directory>

# 가상환경 생성 및 활성화 (선택 사항이나 권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필요 패키지 설치
pip install fastapi uvicorn firebase-admin google-genai pillow python-dotenv python-multipart
