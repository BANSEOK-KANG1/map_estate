# Map Estate — 원룸·다가구 한눈에 보기

Flutter(iOS / Android / Web) + FastAPI로 **오피스텔(원룸)·연립다세대·단독다가구** 실거래
(전월세/매매)와 상권·출퇴근을 한눈에 보는 MVP입니다. (아파트 제외)

## 구조

```
map_estate/
  app/          Flutter 클라이언트
  backend/      FastAPI (캐시·점수·수집)
  docs/         API 키·환경 가이드
```

## 빠른 시작 (데모 데이터)

API 키 없이도 서울 주요 단지 데모 데이터로 UI를 확인할 수 있습니다.

### 1) 백엔드

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

다른 터미널에서 데모 시드:

```bash
curl -X POST http://127.0.0.1:8000/api/demo/seed
```

API 문서: http://127.0.0.1:8000/docs

### 2) Flutter 앱

Flutter SDK가 필요합니다. 없으면 예:

```bash
git clone https://github.com/flutter/flutter.git -b stable --depth 1 ~/flutter_sdk
export PATH="$HOME/flutter_sdk/bin:$PATH"
```

```bash
cd app
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Android 에뮬레이터는 `API_BASE_URL=http://10.0.2.2:8000` 을 쓰세요.  
iOS 시뮬레이터는 `http://127.0.0.1:8000` 이면 됩니다.

빌드 스모크 (이 환경에서 확인됨):
- `flutter build web` ✓
- `flutter build apk --debug` ✓
- `flutter test` ✓


## 실제 실거래 / 상권 연동

자세한 키 발급은 [docs/API_KEYS.md](docs/API_KEYS.md) 참고.

`backend/.env`:

```
MOLIT_SERVICE_KEY=...
KAKAO_REST_KEY=...
```

수집 시작 (서울, 오피스텔/빌라/다가구 · 매매+전월세):

```bash
curl -X POST http://127.0.0.1:8000/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{"months": 12, "sources": ["officetel:rent","villa:rent","multi:rent","officetel:sale","villa:sale","multi:sale"]}'
```

공공데이터에서 아래 API를 활용신청하세요.

- 오피스텔 매매/전월세
- 연립다세대 매매/전월세
- 단독다가구 매매/전월세

지도 타일은 OpenStreetMap을 사용합니다.

## 주요 화면

- 홈: 유형(오피스텔/빌라/다가구)·전월세/매매 필터 + 지도 + 목록
- 상세: 면적 구간별 실거래 추이, 보증금/월세, 인프라, 출퇴근
- 설정: 출근지, 점수 가중치

## API 요약

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/health` | 상태 |
| GET | `/api/regions` | 서울 구 목록 |
| POST | `/api/search` | 조건 검색 |
| GET | `/api/complexes/{id}` | 단지 상세 |
| GET | `/api/complexes/{id}/trends` | 월별 추이 |
| POST | `/api/ingest` | Molit 수집 |
| POST | `/api/demo/seed` | 데모 데이터 |
